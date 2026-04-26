"""Smoke tests for app.py — ensure module imports cleanly and `affected`
is referenced only after it is defined.

Regression guard for the bug where `affected` was used in the timeline
block before being defined in the affected-flights table block.
"""

import ast
import pathlib

APP_PATH = pathlib.Path(__file__).resolve().parents[1] / "app.py"


def test_app_module_parses():
    """app.py must be syntactically valid Python."""
    source = APP_PATH.read_text(encoding="utf-8")
    ast.parse(source)


def test_affected_defined_before_first_use():
    """The variable `affected` must be assigned before any use site.

    This guards against the prior bug where `if not affected.empty:` ran
    before `affected = df_result[...]`.
    """
    source = APP_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    first_def_line: int | None = None
    first_use_line: int | None = None

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "affected":
                    if first_def_line is None or node.lineno < first_def_line:
                        first_def_line = node.lineno
        if isinstance(node, ast.Name) and node.id == "affected" and isinstance(node.ctx, ast.Load):
            if first_use_line is None or node.lineno < first_use_line:
                first_use_line = node.lineno

    assert first_def_line is not None, "expected `affected = ...` assignment in app.py"
    assert first_use_line is not None, "expected at least one read of `affected`"
    assert first_def_line < first_use_line, (
        f"`affected` is used at line {first_use_line} before being defined at line {first_def_line}"
    )
