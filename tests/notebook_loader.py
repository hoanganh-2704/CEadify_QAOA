"""Load the definitions from solution.ipynb without running its experiments.

Only imports, function definitions and UPPERCASE constants are executed, so
the tests run fast and exercise the exact code the notebook uses.
"""
import ast
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NOTEBOOK = REPO / "solution.ipynb"


def _keep(node):
    if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef)):
        return True
    if isinstance(node, ast.Assign):
        names = []
        for target in node.targets:
            elts = target.elts if isinstance(target, ast.Tuple) else [target]
            names += [e.id for e in elts if isinstance(e, ast.Name)]
        return bool(names) and all(name.isupper() for name in names)
    return False


def load_definitions():
    cells = json.loads(NOTEBOOK.read_text(encoding="utf-8"))["cells"]
    module = ast.Module(body=[], type_ignores=[])
    for cell in cells:
        if cell["cell_type"] != "code":
            continue
        tree = ast.parse("".join(cell["source"]))
        module.body += [node for node in tree.body if _keep(node)]
    namespace = {}
    sys.path.insert(0, str(REPO))
    cwd = os.getcwd()
    os.chdir(REPO)
    try:
        exec(compile(module, str(NOTEBOOK), "exec"), namespace)
    finally:
        os.chdir(cwd)
    return namespace
