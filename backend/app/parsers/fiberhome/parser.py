from __future__ import annotations

from app.models.enums import Vendor
from app.models.universal_core import OLTConfig
from app.parsers.base import BaseParser, ParserResult
from app.parsers.capabilities import ParserCapabilities
from app.parsers.fiberhome.onu import parse_onus
from app.parsers.fiberhome.pon import parse_pons
from app.parsers.fiberhome.service import parse_service_bindings
from app.parsers.fiberhome.vlan import parse_vlans
from app.parsers.registry import register_parser


@register_parser
class FiberhomeParser(BaseParser):
    vendor = Vendor.FIBERHOME
    model_family = "GENERIC"
    confidence_signatures = ("fiberhome", "interface gpon", "service-port")
    capabilities = ParserCapabilities(
        vlans=True,
        pons=True,
        onus=True,
        service_bindings=True,
        qos_partial=False,
        multicast=False,
    )

    def parse(self, config_text: str) -> ParserResult:
        lines = config_text.splitlines()
        cfg = OLTConfig(
            vendor=self.vendor,
            model=self.model_family,
            vlans=parse_vlans(lines),
            pons=parse_pons(lines),
            onus=parse_onus(lines),
            service_bindings=parse_service_bindings(lines),
        )
        return ParserResult(config=cfg)
