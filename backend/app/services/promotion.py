"""
Promotion engine -- promove `ONU.extra_vendor` (blobs semi-estruturados) para
entidades formais L9 (subscriber edge), preservando proveniencia.

Princ�pio: "promotion by recurrence". Cada campo de extra_vendor que
representa um conceito recorrente e convertido para o modelo formal
correspondente. O extra_vendor permanece como camada de escape para
vendor quirks remanescentes.

Mapeamentos:

  extra_vendor.ssids              -> ONU.ssids[WiFiSSID]
                                  -> ONU.radios[WiFiRadio] (derivado por band)
  extra_vendor.wancfg             -> ONU.wan_bindings[WANBinding(mode=DHCP/IPOE)]
  extra_vendor.pppoe              -> ONU.wan_bindings[WANBinding(mode=PPPOE)]
  extra_vendor.wan_bindings       -> ONU.wan_bindings (parsed do ZTE wan ethuni)
  extra_vendor.port_routes        -> ONU.port_routes[PortRoute]
  extra_vendor.switchport_bind    -> ONU.bridge_groups[BridgeGroup] (eth<->veip)
  extra_vendor.wps_enabled        -> marca SSID com WPS (atributo opcional)
  extra_vendor.bandwidth_ep       -> permanece (ja em DBA via service_ba)
  extra_vendor.lan_isolation      -> EthernetPort.isolation_enabled
  extra_vendor.loop_detect        -> EthernetPort.loop_detect_enabled

Cada nova entidade carrega `Provenance(source=PROMOTION, confidence)`.
Quando ha ambiguidade (ex: SSID em radio desconhecido), `confidence` e
reduzida e `needs_review=True`.
"""
from __future__ import annotations

import copy
from typing import Any

from app.models import (
    BridgeGroup,
    EthernetPort,
    LANService,
    OLTConfig,
    ONU,
    PortRoute,
    Provenance,
    WANBinding,
    WANMode,
    WiFiBand,
    WiFiRadio,
    WiFiSSID,
)
from app.models.provenance import ProvenanceSource
from app.models.subscriber_edge import WiFiAuthMode
from app.utils.logger import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------
def promote_subscriber_edge(config: OLTConfig) -> OLTConfig:
    """
    Roda em copia profunda; promove extra_vendor -> modelos formais L9.

    Instrumentacao:
      - `extra_vendor_seen`: somatorio de cada key observada em ALGUMA ONU.
      - `extra_vendor_onus`: numero de ONUs com qualquer key promovivel.
      - per-promotion stats: ssids/radios/wan_bindings/port_routes/bridge_groups.
      - `errors`: por ONU, lista de tracebacks compactos das promocoes que
        falharam (best-effort por ONU; nao propaga).
    """
    cfg = copy.deepcopy(config)
    stats = {
        "ssids": 0,
        "radios": 0,
        "wan_bindings": 0,
        "port_routes": 0,
        "bridge_groups": 0,
    }
    # Map wan_profile.id -> wan_profile.name para que _promote_huawei_wan
    # consiga preencher WANBinding.wan_profile_ref com NOME (integridade).
    _wan_pid_to_name: dict[int, str] = {
        getattr(wp, "profile_id", None) or 0: wp.name
        for wp in getattr(cfg, "wan_profiles", [])
        if getattr(wp, "name", None)
    }
    def _promote_huawei_wan_bound(onu, st):
        return _promote_huawei_wan(onu, st, _wan_pid_to_name)
    extra_seen: dict[str, int] = {
        "ssids": 0, "wancfg": 0, "pppoe": 0, "wan_bindings": 0,
        "port_routes": 0, "switchport_bind": 0,
        "wan_config_hw": 0, "internet_config_hw": 0,
        "policy_route_config_hw": 0, "ipconfig_hw": 0,
    }
    extra_onus = 0
    errors: list[dict[str, Any]] = []

    for onu in cfg.onus:
        seen_keys = [k for k in extra_seen if onu.extra_vendor.get(k)]
        if seen_keys:
            extra_onus += 1
            for k in seen_keys:
                v = onu.extra_vendor[k]
                extra_seen[k] += len(v) if isinstance(v, (list, tuple, dict)) else 1

        for fn in (
            _promote_ssids,
            _promote_wancfg,
            _promote_pppoe,
            _promote_wan_bindings,
            _promote_huawei_wan_bound,
            _promote_port_routes,
            _promote_switchport_bind,
        ):
            try:
                fn(onu, stats)
            except Exception as exc:  # noqa: BLE001
                import traceback
                errors.append({
                    "onu": f"{onu.pon_interface}:{onu.onu_id}",
                    "fn": fn.__name__,
                    "exc": repr(exc),
                    "tb": traceback.format_exc(limit=4),
                })
        try:
            _propagate_eth_attrs(onu)
        except Exception as exc:  # noqa: BLE001
            errors.append({
                "onu": f"{onu.pon_interface}:{onu.onu_id}",
                "fn": "_propagate_eth_attrs",
                "exc": repr(exc),
            })

    log.info(
        "promotion_done",
        onus_total=len(cfg.onus),
        extra_vendor_onus=extra_onus,
        extra_vendor_seen=extra_seen,
        errors=len(errors),
        **stats,
    )
    if errors:
        log.warning("promotion_errors", count=len(errors), sample=errors[:3])
        try:
            from pathlib import Path
            import json as _json
            (Path(__file__).resolve().parents[3] / "docs" / "promotion_errors.json").write_text(
                _json.dumps(errors, indent=2, default=str), encoding="utf-8"
            )
        except Exception:  # noqa: BLE001
            pass
    return cfg


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------
def _prov(source: ProvenanceSource, conf: float, reason: str) -> Provenance:
    return Provenance(
        source=source,
        confidence=conf,
        reason=reason,
        needs_review=conf < 0.7,
    )


def _ensure_radio(onu: ONU, band: WiFiBand) -> WiFiRadio:
    for r in onu.radios:
        if r.band == band:
            return r
    radio = WiFiRadio(
        radio_id=len(onu.radios),
        band=band,
        provenance=_prov(ProvenanceSource.SYNTHESIS, 0.6, f"Radio {band.value} inferido por SSID"),
    )
    onu.radios.append(radio)
    return radio


def _promote_ssids(onu: ONU, stats: dict[str, int]) -> None:
    raw_ssids = onu.extra_vendor.get("ssids", [])
    radios_before = len(onu.radios)
    for idx, raw in enumerate(raw_ssids):
        name = (raw.get("name") or "").lower()
        if "5g" in name or "5ghz" in name:
            band = WiFiBand.BAND_5G
        else:
            band = WiFiBand.BAND_2_4G
        radio = _ensure_radio(onu, band)

        auth_raw = (raw.get("authmode") or "").lower()
        auth_map = {
            "wpa2psk": WiFiAuthMode.WPA2_PSK,
            "wpa-psk": WiFiAuthMode.WPA_PSK,
            "wpapsk": WiFiAuthMode.WPA_PSK,
            "wpa3psk": WiFiAuthMode.WPA3_PSK,
            "open": WiFiAuthMode.OPEN,
        }
        auth = auth_map.get(auth_raw, WiFiAuthMode.UNKNOWN)

        ssid = WiFiSSID(
            ssid_id=idx,
            radio_id=radio.radio_id,
            name=raw.get("name"),
            enabled=raw.get("enabled", True),
            hidden=raw.get("hide", False),
            auth_mode=auth,
            encryption=raw.get("encrypt"),
            key_present=raw.get("key_present", False),
            provenance=_prov(
                ProvenanceSource.PROMOTION,
                0.9,
                "Promovido de extra_vendor.ssids",
            ),
        )
        onu.ssids.append(ssid)
        stats["ssids"] += 1
    stats["radios"] += (len(onu.radios) - radios_before)
    if raw_ssids:
        onu.wifi_enabled = True


def _promote_wancfg(onu: ONU, stats: dict[str, int]) -> None:
    raw_list = onu.extra_vendor.get("wancfg", [])
    for raw in raw_list:
        mode = WANMode.DHCP if raw.get("ip_stack_mode") else WANMode.BRIDGE
        binding = WANBinding(
            binding_id=raw.get("index", 1),
            mode=mode,
            ip_stack_mode=raw.get("ip_stack_mode"),
            ipv6_src_type=raw.get("ipv6_src_type"),
            prefix_src_type=raw.get("prefix_src_type"),
            provenance=_prov(
                ProvenanceSource.PROMOTION,
                0.85,
                f"Promovido de extra_vendor.wancfg (ind={raw.get('index')})",
            ),
        )
        onu.wan_bindings.append(binding)
        stats["wan_bindings"] += 1


def _promote_pppoe(onu: ONU, stats: dict[str, int]) -> None:
    raw_list = onu.extra_vendor.get("pppoe", [])
    for raw in raw_list:
        binding = WANBinding(
            binding_id=raw.get("index", 1),
            mode=WANMode.PPPOE,
            nat_enabled=str(raw.get("nat", "")).lower() == "enable",
            pppoe_user=raw.get("user"),
            pppoe_password_present=raw.get("password_present", False),
            provenance=_prov(
                ProvenanceSource.PROMOTION,
                0.95,
                "Promovido de extra_vendor.pppoe (ZTE pon-onu-mng pppoe)",
            ),
        )
        onu.wan_bindings.append(binding)
        stats["wan_bindings"] += 1


def _promote_wan_bindings(onu: ONU, stats: dict[str, int]) -> None:
    raw_list = onu.extra_vendor.get("wan_bindings", [])
    next_id = 100
    for raw in raw_list:
        binding = WANBinding(
            binding_id=next_id,
            mode=WANMode.UNKNOWN,
            provenance=_prov(
                ProvenanceSource.PROMOTION,
                0.6,
                f"Promovido de extra_vendor.wan_bindings (raw: {str(raw)[:80]})",
            ),
        )
        onu.wan_bindings.append(binding)
        stats["wan_bindings"] += 1
        next_id += 1



def _promote_huawei_wan(onu: ONU, stats: dict[str, int], wan_profile_names_by_id: dict[int, str] | None = None) -> None:
    """
    Huawei MA5800: `ont wan-config slot port ip-index N profile-id PID` cria
    um WANBinding referenciando o wan_profile (resolvendo PID -> nome).
    `ont ipconfig ... pppoe user-account username ...` -> WANBinding(mode=PPPOE).
    """
    wan_profile_names_by_id = wan_profile_names_by_id or {}
    raw_wc = onu.extra_vendor.get("wan_config_hw", [])
    raw_ip = onu.extra_vendor.get("ipconfig_hw", [])
    for wc in raw_wc:
        pid = wc.get("profile_id")
        ref_name = wan_profile_names_by_id.get(pid) if pid is not None else None
        binding = WANBinding(
            binding_id=wc.get("ip_index", 1),
            mode=WANMode.UNKNOWN,
            wan_profile_ref=ref_name,
            provenance=_prov(
                ProvenanceSource.PROMOTION,
                0.85,
                f"Promovido de extra_vendor.wan_config_hw (ip_index={wc.get('ip_index')} profile_id={wc.get('profile_id')})",
            ),
        )
        onu.wan_bindings.append(binding)
        stats["wan_bindings"] += 1
    for ip in raw_ip:
        mode = WANMode.PPPOE if ip.get("mode") == "pppoe" else WANMode.UNKNOWN
        binding = WANBinding(
            binding_id=(ip.get("ip_index") or 1) + 1000,
            mode=mode,
            pppoe_user=ip.get("pppoe_user"),
            pppoe_password_present=bool(ip.get("pppoe_user")),
            provenance=_prov(
                ProvenanceSource.PROMOTION,
                0.9 if mode == WANMode.PPPOE else 0.6,
                "Promovido de extra_vendor.ipconfig_hw (Huawei ont ipconfig)",
            ),
        )
        onu.wan_bindings.append(binding)
        stats["wan_bindings"] += 1


def _promote_port_routes(onu: ONU, stats: dict[str, int]) -> None:
    raw_list = onu.extra_vendor.get("port_routes", [])
    eth_ids = {e.port_id for e in onu.eth_ports}
    for raw in raw_list:
        if isinstance(raw, dict):
            eth_id = raw.get("eth", 1) or 1
            # Garante que EthernetPort para esse eth_id existe (port-route
            # so faz sentido se a porta existe na ONU). Evita cross-binding
            # broken no validador.
            if eth_id not in eth_ids:
                onu.eth_ports.append(EthernetPort(port_id=eth_id))
                eth_ids.add(eth_id)
            route = PortRoute(
                src_port_id=eth_id,
                dst_port_id=eth_id,
                enabled=raw.get("enabled", True),
                provenance=_prov(
                    ProvenanceSource.PROMOTION, 0.8,
                    "Promovido de Huawei `ont port route`",
                ),
            )
        else:
            route = PortRoute(
                src_port_id=0, dst_port_id=0,
                description=str(raw)[:100],
                provenance=_prov(
                    ProvenanceSource.PROMOTION, 0.4,
                    f"Raw port route: {raw}",
                ),
            )
        onu.port_routes.append(route)
        stats["port_routes"] += 1


def _promote_switchport_bind(onu: ONU, stats: dict[str, int]) -> None:
    raw_list = onu.extra_vendor.get("switchport_bind", [])
    if not raw_list:
        return
    members = sorted({r["eth"] for r in raw_list if isinstance(r, dict) and "eth" in r})
    group = BridgeGroup(
        group_id=1,
        name="ZTE-DEFAULT-BRIDGE",
        member_port_ids=members,
        provenance=_prov(
            ProvenanceSource.PROMOTION,
            0.75,
            "Promovido de switchport-bind eth->veip (ZTE bridge mode)",
        ),
    )
    onu.bridge_groups.append(group)
    stats["bridge_groups"] += 1


def _propagate_eth_attrs(onu: ONU) -> None:
    isolation = onu.extra_vendor.get("lan_isolation")
    loop_detect = onu.extra_vendor.get("loop_detect") or {}
    for eth in onu.eth_ports:
        if isolation is not None:
            eth.isolation_enabled = bool(isolation)
        if isinstance(loop_detect, dict) and eth.port_id in loop_detect:
            eth.loop_detect_enabled = bool(loop_detect[eth.port_id])


__all__ = ["promote_subscriber_edge"]
