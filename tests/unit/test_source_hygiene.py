"""Source checks that no linter of the project runs."""

import ast
import os

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")


def test_no_function_has_a_decorator_twice():
    """A doubled @staticmethod is only callable on Python 3.10+ (a
    'staticmethod' object is not callable on QGIS builds with 3.9)."""
    doubled = []
    for folder, _, names in os.walk(SRC):
        for name in names:
            if not name.endswith(".py"):
                continue
            path = os.path.join(folder, name)
            with open(path, encoding="utf-8") as handle:
                tree = ast.parse(handle.read(), path)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    decorators = [ast.dump(d) for d in node.decorator_list]
                    if len(decorators) != len(set(decorators)):
                        doubled.append(f"{os.path.relpath(path, SRC)}:{node.lineno} {node.name}")
    assert not doubled
