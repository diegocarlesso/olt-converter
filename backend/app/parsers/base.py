from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar

from app.models.enums import Vendor
from app.models.universal_core import OLTConfig
from app.parsers.capabilities import ParserCapabilities


@dataclass
class ParserResult:
    config: OLTConfig
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    unparsed_lines: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


class BaseParser(ABC):
    vendor: ClassVar[Vendor] = Vendor.UNKNOWN
    model_family: ClassVar[str] = ""
    confidence_signatures: ClassVar[tuple[str, ...]] = ()
    capabilities: ClassVar[ParserCapabilities] = ParserCapabilities()

    @abstractmethod
    def parse(self, config_text: str) -> ParserResult:
        raise NotImplementedError

    @classmethod
    def detect(cls, config_text: str) -> float:
        if not cls.confidence_signatures:
            return 0.0
        text = config_text.lower()
        hits = sum(1 for sig in cls.confidence_signatures if sig.lower() in text)
        return hits / len(cls.confidence_signatures)
