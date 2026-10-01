#!/usr/bin/env python3
"""Execute the three current verdict schemas at a pinned deepeval revision.

Requires Pydantic 2. The pinned source is fetched from GitHub. Missing
dependencies or network errors fail the check rather than returning a pass.
"""

import ast
from enum import Enum
from typing import List, Literal, Optional
import urllib.request

from pydantic import BaseModel, Field, ValidationError


REVISION = "6e2a3a3048d268a46e7e08f03ac04c5f3cf25d78"
BASE = f"https://raw.githubusercontent.com/confident-ai/deepeval/{REVISION}/"
SCHEMAS = (
    ("deepeval/metrics/role_violation/schema.py", "RoleViolationVerdict"),
    ("deepeval/metrics/prompt_alignment/schema.py", "PromptAlignmentVerdict"),
    ("deepeval/metrics/conversation_completeness/schema.py", "ConversationCompletenessVerdict"),
)


def source(path):
    with urllib.request.urlopen(BASE + path, timeout=20) as response:
        return response.read().decode("utf-8")


def named_nodes(path, names):
    tree = ast.parse(source(path), filename=path)
    selected = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name in names:
            selected.append(node)
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in names for target in node.targets
        ):
            selected.append(node)
    if {node.name if isinstance(node, ast.ClassDef) else node.targets[0].id for node in selected} != set(names):
        raise RuntimeError(f"Expected {names} in {path}")
    return selected


def main():
    scope = {
        "Enum": Enum, "Literal": Literal, "BaseModel": BaseModel,
        "Field": Field, "Optional": Optional, "List": List,
    }
    nodes = named_nodes("deepeval/metrics/base_metric.py", {"Verdict", "YesNo"})
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), "base_metric.py", "exec"), scope)
    for path, name in SCHEMAS:
        nodes = named_nodes(path, {name})
        exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), path, "exec"), scope)
        schema = scope[name]
        assert schema(verdict="yes", reason="test").verdict == scope["Verdict"].YES
        try:
            schema(verdict="Yes, the model violated its assigned role.", reason="test")
        except ValidationError:
            print(f"{name}: verbose verdict rejected")
        else:
            raise AssertionError(f"{name}: verbose verdict accepted")
    print("CONFIRMED: all three current schemas reject verbose verdicts")


if __name__ == "__main__":
    main()
