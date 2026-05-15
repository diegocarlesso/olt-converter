"""Renderer Fiberhome AN5516 — emite sintaxe WOS CLI (set/add ...)."""
from __future__ import annotations

from app.models import OLTConfig, Vendor
from app.renderers.base import BaseRenderer
from app.renderers.registry import register_renderer
from app.services.mapping import map_interface


@register_renderer
class FiberhomeAN5516Renderer(BaseRenderer):
    vendor = Vendor.FIBERHOME
    model_family = "AN5516"
    template_dir = "fiberhome/an5516"

    def render(self, config: OLTConfig) -> str:
        ctx = self._context(config)
        blocks = [
            self._render("header.j2", **ctx),
            self._render("system.j2", **ctx),
            self._render("boards.j2", **ctx),
            self._render("vlan.j2", **ctx),
            self._render("service_vlan.j2", **ctx),
            self._render("profiles.j2", **ctx),
            self._render("interfaces.j2", **ctx),
            self._render("pon.j2", **ctx),
            self._render("whitelist.j2", **ctx),
        ]
        return self._join(*blocks)

    def _context(self, config: OLTConfig) -> dict:
        return {
            "config": config,
            "hostname": config.hostname,
            "boards": config.boards,
            "vlans": config.vlans,
            "service_vlans": config.service_vlans,
            "uplinks": [
                {
                    "interface": map_interface(u.interface, config.vendor, self.vendor),
                    "raw": u,
                }
                for u in config.uplinks
            ],
            "pons": [
                {
                    "interface": map_interface(p.interface, config.vendor, self.vendor, kind="gpon"),
                    "raw": p,
                    "onus": p.onus,
                }
                for p in config.pons
            ],
            "onus": config.onus,
            "service_ports": config.service_ports,
            "dba_profiles": config.dba_profiles,
            "service_profiles": config.service_profiles,
            "onu_type_profiles": config.onu_type_profiles,
            "mgmt_vlans": [v for v in config.vlans if v.is_management],
            "static_routes": config.static_routes,
            "radius_servers": config.radius_servers,
            "users": config.users,
        }
