"""Renderer Datacom DM4615 (DmOS)."""
from __future__ import annotations

from app.models import OLTConfig, Vendor
from app.renderers.base import BaseRenderer
from app.renderers.registry import register_renderer
from app.services.mapping import map_interface


@register_renderer
class DatacomDM4615Renderer(BaseRenderer):
    vendor = Vendor.DATACOM
    model_family = "DM4615"
    template_dir = "datacom/dm4615"

    def render(self, config: OLTConfig) -> str:
        ctx = self._build_context(config)
        blocks = [
            self._render("header.j2", **ctx),
            self._render("system.j2", **ctx),
            self._render("vlan.j2", **ctx),
            self._render("uplinks.j2", **ctx),
            self._render("gpon.j2", **ctx),
            self._render("footer.j2", **ctx),
        ]
        return self._join(*blocks)

    def _build_context(self, config: OLTConfig) -> dict:
        return {
            "config": config,
            "hostname": config.hostname,
            "vlans": config.vlans,
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
            "dba_profiles": config.dba_profiles,
        }
