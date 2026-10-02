import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))  # type: ignore[import-unresolved]

from ir_to_markdown import compile_markdown  # type: ignore[import-unresolved]


def test_compile_markdown_preserves_ir_contract() -> None:
    root = Path(__file__).parents[1]
    ir = json.loads((root / "templates" / "intermediate_representation.json").read_text())
    output = compile_markdown(ir)
    assert "# UI Implementation Contract" in output
    assert "`page`" in output
    assert "Clone any interface, pixel for pixel." in output
    assert "#5b8cff" in output
    assert "`Button`" in output
    assert "SSIM minimum" in output
