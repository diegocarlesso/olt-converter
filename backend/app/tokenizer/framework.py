from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    line: int
    indent: int


class Tokenizer:
    def tokenize(self, config_text: str) -> list[Token]:
        tokens: list[Token] = []
        for i, raw in enumerate(config_text.splitlines(), start=1):
            indent = len(raw) - len(raw.lstrip(" "))
            stripped = raw.strip()
            if not stripped:
                tokens.append(Token("blank", "", i, indent))
            elif stripped.startswith("#") or stripped.startswith("!"):
                tokens.append(Token("comment", stripped, i, indent))
            elif stripped.lower().startswith("interface "):
                tokens.append(Token("block_start", stripped, i, indent))
            else:
                tokens.append(Token("statement", stripped, i, indent))
        return tokens
