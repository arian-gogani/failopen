#!/usr/bin/env python3
"""Test the initial and hardened PR functions, fetched by pinned commit SHA."""

from __future__ import annotations

import ast
import asyncio
import contextlib
import io
import os
import urllib.request


PATH = "python/samples/agentchat_external_governance/main.py"
BASE = "https://raw.githubusercontent.com/jw-ond/autogen"
INITIAL = "0cd67042ab4bb65653c9ba454f9c3bd60b0829e0"
HARDENED = "ec6cf48c026b1a879ef2063fbe5404482d40c873"
VERDICTS = ("deny", "require_approval", "allow", "denied", "DENY", "block", "error", "", None)
UNKNOWN = ("denied", "DENY", "block", "error", "", None)
ACTION_HASH = "a" * 64


def functions_at(revision: str, names: set[str]) -> dict:
    url = f"{BASE}/{revision}/{PATH}"
    with urllib.request.urlopen(url, timeout=15) as response:
        source = response.read().decode("utf-8")
    tree = ast.parse(source, filename=url)
    selected = [
        ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0),
        *(node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names),
    ]
    found = {node.name for node in selected if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if found != names:
        raise RuntimeError(f"Expected {names} at {revision}, found {found}")
    scope = {"os": os}
    compiled = compile(ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])), url, "exec")
    exec(compiled, scope)
    return scope


async def dispatch_results(revision: str) -> dict:
    scope = functions_at(revision, {"governed_export_customer_records"})
    scope["build_action_envelope"] = lambda **kwargs: {"action_hash": ACTION_HASH}
    outcomes = {}
    for verdict in VERDICTS:
        async def checkpoint(_envelope):
            return {"verdict": verdict, "decision_id": "test", "action_hash": ACTION_HASH, "reason": "test"}

        scope["call_external_governance"] = checkpoint
        with contextlib.redirect_stdout(io.StringIO()):
            result = await scope["governed_export_customer_records"]("a", "b", 1, False)
        outcomes[repr(verdict)] = result["status"]
    return outcomes


async def main() -> None:
    old = await dispatch_results(INITIAL)
    new = await dispatch_results(HARDENED)
    for verdict in VERDICTS:
        key = repr(verdict)
        print(f"{key:20} initial={old[key]:18} hardened={new[key]}")
    assert all(old[repr(v)] == "executed" for v in UNKNOWN)
    assert all(new[repr(v)] == "blocked" for v in UNKNOWN)
    assert old[repr("allow")] == new[repr("allow")] == "executed"
    assert old[repr("deny")] == new[repr("deny")] == "blocked"
    assert old[repr("require_approval")] == new[repr("require_approval")] == "approval_required"

    scope = functions_at(HARDENED, {"blocked_decision", "normalize_governance_decision"})
    for verdict in UNKNOWN:
        got = scope["normalize_governance_decision"](
            {"action_hash": ACTION_HASH}, {"verdict": verdict, "action_hash": ACTION_HASH}
        )
        assert got["verdict"] == "deny", (verdict, got)
    print("CONFIRMED: six initial fallthroughs; zero at hardened head; parser also denies all six")


if __name__ == "__main__":
    asyncio.run(main())
