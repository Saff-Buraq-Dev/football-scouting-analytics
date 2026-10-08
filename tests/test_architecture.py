"""Enforce the layer dependency rule (docs/ARCHITECTURE.md §2).

Each layer may only import the project layers listed for it. In particular the
canonical model and analytics must never depend on a provider.
"""

import ast
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src" / "football_platform"
PACKAGE = "football_platform"

ALLOWED_IMPORTS = {
    "canonical": {"canonical"},
    "providers": {"canonical", "providers"},
    "analytics": {"canonical", "analytics"},
    "database": {"canonical", "database"},
    "pipeline": {"canonical", "providers", "database", "pipeline"},
    "api": {"canonical", "analytics", "database", "api", "auth", "board"},
    "auth": {"auth"},
    "board": {"database", "board"},
    "reports": {"canonical", "analytics", "database", "reports"},
}


def project_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    layers = set()
    for node in ast.walk(tree):
        modules = []
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules = [node.module]
        for module in modules:
            parts = module.split(".")
            if parts[0] == PACKAGE and len(parts) > 1:
                layers.add(parts[1])
    return layers


SOURCE_FILES = sorted(p for p in PACKAGE_ROOT.rglob("*.py") if p.parent != PACKAGE_ROOT)


@pytest.mark.parametrize("path", SOURCE_FILES, ids=lambda p: str(p.relative_to(PACKAGE_ROOT)))
def test_layer_imports_respect_dependency_rule(path):
    layer = path.relative_to(PACKAGE_ROOT).parts[0]
    assert layer in ALLOWED_IMPORTS, f"Unknown layer {layer!r}: add it to ALLOWED_IMPORTS"
    forbidden = project_imports(path) - ALLOWED_IMPORTS[layer]
    assert not forbidden, f"{path.name} ({layer}) imports forbidden layers {forbidden}"
