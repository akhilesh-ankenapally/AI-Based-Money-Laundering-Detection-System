"""Check dependencies and imports needed to run the AML platform."""

import importlib
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent


REQUIRED_IMPORTS = [
    ("ply", "ply"),
    ("networkx", "networkx"),
    ("pandas", "pandas"),
    ("matplotlib", "matplotlib"),
    ("numpy", "numpy"),
    ("scikit-learn", "sklearn"),
    ("streamlit", "streamlit"),
    ("plotly", "plotly"),
]

PROJECT_IMPORTS = [
    "compiler.lexer",
    "compiler.parser",
    "analysis.pipeline",
    "graph.transaction_graph",
    "exports.report_export",
]


def check_import(display_name, module_name):
    """Import one module and print a viva-friendly status line."""
    try:
        importlib.import_module(module_name)
    except ImportError as error:
        print(display_name + " MISSING")
        print("  Install with: python -m pip install " + display_name)
        print("  Details: " + str(error))
        return False
    print(display_name + " OK")
    return True


def main():
    """Validate third-party and project imports without starting Streamlit."""
    print("Python: " + sys.version.split()[0])
    print("Project root: " + str(PROJECT_ROOT))
    print()

    all_ok = True
    for display_name, module_name in REQUIRED_IMPORTS:
        all_ok = check_import(display_name, module_name) and all_ok

    for module_name in PROJECT_IMPORTS:
        all_ok = check_import(module_name, module_name) and all_ok

    if not all_ok:
        print("\nEnvironment validation failed.")
        print("Run: python -m pip install -r requirements.txt")
        return 1

    print("\nEnvironment validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())