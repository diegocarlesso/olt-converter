from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.models.universal_core import OLTConfig


def render_fiberhome_to_huawei(config: OLTConfig) -> str:
    env = Environment(loader=FileSystemLoader(str(Path(__file__).parent / "templates")))
    template = env.get_template("fiberhome_to_huawei.j2")
    return template.render(header="sysname MIGRATED", footer="return", vlans=config.vlans, service_bindings=config.service_bindings)
