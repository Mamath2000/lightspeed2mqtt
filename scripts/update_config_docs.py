"""Synchronize README/Quickstart snippets with config.example and field metadata."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lightspeed.config_docs import render_config_field_table  # noqa: E402

DOC_TARGETS = [
    ROOT / "README.md",
    ROOT / "specs/001-logi-integration/quickstart.md",
]


def _replace_block(text: str, marker: str, payload: str) -> str:
    start = f"<!-- {marker}:start -->"
    end = f"<!-- {marker}:end -->"
    if start not in text or end not in text:
        raise RuntimeError(f"Impossible de trouver les bornes {marker}")
    before, rest = text.split(start, 1)
    _existing, after = rest.split(end, 1)
    return f"{before}{start}\n{payload}\n{end}{after}"


def main() -> None:
    config_text = (ROOT / "config.example.yaml").read_text(encoding="utf-8").strip()
    snippet = f"```yaml\n{config_text}\n```"
    table = render_config_field_table()

    for path in DOC_TARGETS:
        text = path.read_text(encoding="utf-8")
        text = _replace_block(text, "config-example", snippet)
        text = _replace_block(text, "config-table", table)
        path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
