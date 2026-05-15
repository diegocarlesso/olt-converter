from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.models.universal_core import OLTConfig


@dataclass
class ParserResult:
    config: OLTConfig
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class BaseParser(ABC):
    @classmethod
    @abstractmethod
    def detect(cls, config_text: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def parse(self, config_text: str) -> OLTConfig:
        raise NotImplementedError
