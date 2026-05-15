"""Parsers modulares por vendor/modelo.

Cada subpacote (fiberhome/, zte/, huawei/, datacom/) expõe um parser
concreto. Todos eles herdam de `BaseParser` e retornam uma instância de
`OLTConfig`.

Use `parser_registry` para resolver dinamicamente o parser correto a partir
do vendor detectado.
"""
from app.parsers.base import BaseParser, ParserResult
from app.parsers.registry import detect_vendor, get_parser, parser_registry

__all__ = [
    "BaseParser",
    "ParserResult",
    "detect_vendor",
    "get_parser",
    "parser_registry",
]
