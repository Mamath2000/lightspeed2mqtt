from __future__ import annotations

import textwrap
from pathlib import Path

from lightspeed.config_docs import render_config_field_table

REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"
QUICKSTART_PATH = REPO_ROOT / "specs/001-logi-integration/quickstart.md"


def _extract_block(text: str, marker: str) -> str:
    start = f"<!-- {marker}:start -->"
    end = f"<!-- {marker}:end -->"
    if start not in text or end not in text:
        raise AssertionError(f"Bloc {marker} manquant")
    return text.split(start, 1)[1].split(end, 1)[0].strip()


def _normalize_yaml(text: str) -> str:
    stripped = textwrap.dedent(text.strip("\n"))
    return "\n".join(line.rstrip() for line in stripped.splitlines())


def test_docs_embed_config_example():
    config_text = _normalize_yaml((REPO_ROOT / "config.example.yaml").read_text(encoding="utf-8"))
    expected_block = f"```yaml\n{config_text}\n```"

    for path in (README_PATH, QUICKSTART_PATH):
        doc_text = path.read_text(encoding="utf-8")
        block = _normalize_yaml(_extract_block(doc_text, "config-example"))
        assert block == _normalize_yaml(expected_block)


def test_docs_share_same_field_table():
    expected_table = render_config_field_table().strip()
    for path in (README_PATH, QUICKSTART_PATH):
        doc_text = path.read_text(encoding="utf-8")
        block = _extract_block(doc_text, "config-table")
        assert block.strip() == expected_table
