from __future__ import annotations

from app.models.universal_core import OLTConfig
from app.parsers.base import BaseParser
from app.parsers.capabilities import ParserCapabilities
from app.parsers.fiberhome.onu import parse_onus
from app.parsers.fiberhome.pon import parse_pons
from app.parsers.fiberhome.service import parse_service_bindings
from app.parsers.fiberhome.vlan import parse_vlans


class FiberhomeParser(BaseParser):
    capabilities = ParserCapabilities(vlans=True, pons=True, onus=True, service_bindings=True, qos_partial=False, multicast=False)
    @classmethod
    def detect(cls, config_text: str) -> bool:
        lowered = config_text.lower()
        return "fiberhome" in lowered or "interface gpon" in lowered

    def parse(self, config_text: str) -> OLTConfig:
        lines = config_text.splitlines()
        return OLTConfig(
            vendor="fiberhome",
            vlans=parse_vlans(lines),
            pons=parse_pons(lines),
            onus=parse_onus(lines),
            service_bindings=parse_service_bindings(lines),
        )
