"""Renderer ZTE C300/C320/C600 — emite CLI completo a partir de OLTConfig."""
from __future__ import annotations

from app.models import OLTConfig, Vendor
from app.renderers.base import BaseRenderer
from app.renderers.registry import register_renderer
from app.services.mapping import map_interface


@register_renderer
class ZTEC600Renderer(BaseRenderer):
    vendor = Vendor.ZTE
    model_family = "C600"
    template_dir = "zte/c600"

    def render(self, config: OLTConfig) -> str:
        ctx = self._context(config)
        blocks = [
            self._render("header.j2", **ctx),
            self._render("system.j2", **ctx),
            self._render("vlan.j2", **ctx),
            self._render("interfaces.j2", **ctx),
            self._render("profiles.j2", **ctx),
            self._render("pon.j2", **ctx),
            self._render("service_port.j2", **ctx),
            self._render("footer.j2", **ctx),
        ]
        return self._join(*blocks)

    # ---- contexto rico p/ os templates --------------------------------
    def _context(self, config: OLTConfig) -> dict:
        # Uplinks traduzidos para o vocabulário ZTE
        uplinks = []
        for u in config.uplinks:
            uplinks.append(
                {
                    "interface": map_interface(u.interface, config.vendor, self.vendor),
                    "description": u.description,
                    "enabled": u.enabled,
                    "native_vlan": u.native_vlan,
                    "allowed_vlans": u.allowed_vlans,
                    "raw": u,
                }
            )

        # PONs + ONUs com ethernet ports detalhados
        pons = []
        for p in config.pons:
            pons.append(
                {
                    "interface": map_interface(p.interface, config.vendor, self.vendor, kind="gpon"),
                    "description": p.description,
                    "admin_state": p.admin_state,
                    "ont_auto_find": p.ont_auto_find,
                    # Passa ONU objects diretamente (não dicts) p/ template consultar
                    # service_profile_name, line_profile_name, eth_ports etc. consistentemente
                    "onus": p.onus,
                }
            )

        service_ports = []
        for sp in config.service_ports:
            service_ports.append(
                {
                    "id": sp.service_port_id,
                    "pon": map_interface(sp.pon_interface, config.vendor, self.vendor, kind="gpon"),
                    "onu_id": sp.onu_id,
                    "gem_id": sp.gem_id or 1,
                    "match_vlan": sp.match_vlan,
                    "action": sp.action.value if hasattr(sp.action, "value") else str(sp.action),
                    "target_vlan": sp.target_vlan or sp.match_vlan,
                    "user_vlan": sp.user_vlan,
                }
            )

        # Profiles
        dbas = [
            {
                "name": d.name,
                "type_num": d.type.value.replace("type", ""),
                "max": d.max_bandwidth,
                "assured": d.assured_bandwidth,
                "fix": d.fix_bandwidth,
            }
            for d in config.dba_profiles
        ]

        return {
            "config": config,
            "hostname": config.hostname,
            "vlans": config.vlans,
            "uplinks": uplinks,
            "pons": pons,
            "service_ports": service_ports,
            "line_profiles": config.line_profiles,
            "service_profiles": config.service_profiles,
            "dba_profiles": dbas,
            "mgmt_vlans": [v for v in config.vlans if v.is_management],
        }
