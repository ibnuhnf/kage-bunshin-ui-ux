#!/usr/bin/env python3
"""Compile the design IR into an AI-readable Markdown implementation contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _safe(value: Any) -> str:
    if isinstance(value, dict):
        return ", ".join(f"{key}: {_safe(item)}" for key, item in value.items())
    if isinstance(value, list):
        return ", ".join(_safe(item) for item in value)
    return "null" if value is None else str(value).replace("`", "\\`")


def _table(rows: list[tuple[str, Any]]) -> list[str]:
    return ["| Property | Value |", "|---|---|"] + [f"| `{key}` | `{_safe(value)}` |" for key, value in rows]


def compile_markdown(ir: dict[str, Any]) -> str:
    source = ir["source"]
    lines = [
        "# UI Implementation Contract", "",
        "> Generated from the Design IR. HTML, React, Figma, and Stitch outputs must follow this contract.",
        "", "## Source", "", *_table(list(source.items())), "",
        "## Non-Negotiable Rules", "",
        "- Preserve semantic layout; do not replace flow layout with absolute pixel positioning.",
        "- Preserve child order, text content, token references, variants, and interaction states.",
        "- Use responsive behavior implied by `fill`, `hug`, `fixed`, and `wrap`.",
        "- Use accessible semantic elements and visible keyboard focus states.",
        "- If the IR omits a value, state the assumption instead of inventing a token.", "",
        "## Design Tokens", "", "Use these values or their exact semantic equivalents. Do not invent replacements.", "",
    ]
    tokens = ir["tokens"]
    for group, values in tokens.items():
        if group.startswith("$") or not isinstance(values, dict):
            continue
        rows = []
        for name, value in values.items():
            rows.append((name, value.get("hex") if isinstance(value, dict) and "hex" in value else value))
        lines += [f"### {group.title()}", "", *_table(rows), ""]

    layout = ir["layout"]
    lines += ["## Layout Contract", "", f"Root: `{layout['root']}`", "", "Every node must preserve its semantic role, flow, sizing, and child order.", ""]
    for node_id, node in layout["nodes"].items():
        lines += [f"### `{node_id}`", "", f"Role: `{node.get('role', 'unspecified')}`", ""]
        lines += _table([(key, value) for key, value in node.items() if key not in {"role", "children", "$comment"}])
        if node.get("children"):
            lines += ["", "Children: " + " → ".join(f"`{child}`" for child in node["children"])]
        lines += [""]

    lines += ["## Component Contract", "", "Implement reusable components before composing the page. Preserve every variant and state.", ""]
    for name, spec in ir.get("components", {}).items():
        if name.startswith("$"):
            continue
        lines += [f"### `{name}`", "", *_table([(key, value) for key, value in spec.items() if key != "$comment"]), ""]

    verification = ir.get("verification", {})
    lines += ["## Verification Contract", "", "Render at the source viewport, then compare against the source screenshot.", ""]
    lines += _table([("SSIM minimum", ">= 0.95"), ("MAE maximum", "<= 5.0"), ("Iterations", verification.get("iterations", 0)), ("Target", verification.get("target"))])
    lines += ["", "Do not report completion until these gates pass or residual deviations are documented.", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(compile_markdown(json.loads(args.input.read_text(encoding="utf-8"))), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
