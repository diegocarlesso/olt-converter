"""Renderer Huawei MA5800 — emite CLI completo MA5800/MA5680T/MA5608T."""
from __future__ import annotations

from app.models import OLTConfig, Vendor
from app.renderers.base import BaseRenderer
from app.renderers.registry import register_renderer
from app.services.mapping import map_interface


@register_renderer
class HuaweiMA5800Renderer(BaseRenderer):
    vendor = Vendor.HUAWEI
    model_family = "MA5800"
    template_dir = "huawei/ma5800"

    def render(self, config: OLTConfig) -> str:
        ctx = self._context(config)
        blocks = [
            self._render("header.j2", **ctx),
            self._render("boards.j2", **ctx),
            self._render("system.j2", **ctx),
            self._render("traffic_tables.j2", **ctx),
            self._render("dba.j2", **ctx),
            self._render("srvprofiles.j2", **ctx),
            self._render("lineprofiles.j2", **ctx),
            self._render("vlan.j2", **ctx),
            self._render("uplinks.j2", **ctx),
            self._render("gpon.j2", **ctx),
            self._render("onts.j2", **ctx),
            self._render("service_port.j2", **ctx),
            self._render("subscriber_edge.j2", **ctx),
            self._render("footer.j2", **ctx),
        ]
        return self._join(*blocks)

    def _context(self, config: OLTConfig) -> dict:
        uplinks = [
            {
                "interface": map_interface(u.interface, config.vendor, self.vendor),
                "raw": u,
            }
            for u in config.uplinks
        ]
        pons = [
            {
                "interface": map_interface(p.interface, config.vendor, self.vendor, kind="gpon"),
                "raw": p,
                "slot": p.slot,
                "port": p.port,
            }
            for p in config.pons
        ]
        onts = []
        for p in config.pons:
            mapped_iface = map_interface(p.interface, config.vendor, self.vendor, kind="gpon")
            # Huawei: 'gpon 0/slot' → o slot vai como primeiro arg de `ont add`
            slot_str = mapped_iface.replace("gpon ", "").split("/")[1] if "/" in mapped_iface else "0"
            for onu in p.onus:
                onts.append(
                    {
                        "slot": slot_str,
                        "port": onu.pon_port if onu.pon_port is not None else 0,
                        "onu_id": onu.onu_id,
                        "serial_number": onu.serial_number or f"AUTO{onu.onu_id:04d}",
                        "line_profile_id": onu.line_profile_id or 10,
                        "service_profile_id": onu.service_profile_id or 1,
                        "description": onu.description,
                        "vlan_id": onu.native_vlan or onu.user_vlan,
                    }
                )

        service_ports = []
        for sp in config.service_ports:
            service_ports.append(
                {
                    "id": sp.service_port_id,
                    "match_vlan": sp.match_vlan,
                    "pon": map_interface(sp.pon_interface, config.vendor, self.vendor, kind="gpon"),
                    "onu_id": sp.onu_id,
                    "gem_id": sp.gem_id or 1,
                    "user_vlan": sp.user_vlan,
                    "inbound_traffic_profile": sp.inbound_traffic_profile,
                    "outbound_traffic_profile": sp.outbound_traffic_profile,
                }
            )

        # L9 subscriber edge — ONUs com dados promovidos (eth_ports/wan/ssid/routes)
        onts_with_edge = [
            {
                "slot": onu.slot or 0,
                "port": onu.pon_port or 0,
                "onu_id": onu.onu_id,
                "eth_ports": onu.eth_ports,
                "wan_bindings": onu.wan_bindings,
                "ssids": onu.ssids,
                "port_routes": onu.port_routes,
            }
            for onu in config.onus
            if onu.eth_ports or onu.wan_bindings or onu.ssids or onu.port_routes
        ]

        return {
            "config": config,
            "hostname": config.hostname,
            "boards": config.boards,
            "vlans": config.vlans,
            "uplinks": uplinks,
            "pons": pons,
            "onts": onts,
            "onts_with_edge": onts_with_edge,
            "service_ports": service_ports,
            "line_profiles": config.line_profiles,
            "service_profiles": config.service_profiles,
            "dba_profiles": config.dba_profiles,
            "traffic_profiles": config.traffic_profiles,
            "mgmt_vlans": [v for v in config.vlans if v.is_management],
        }
