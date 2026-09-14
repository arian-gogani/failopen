#!/usr/bin/env python3
"""Run the reproductions.

    python3 run.py            list the cases
    python3 run.py deepeval   run one
    python3 run.py --all      run all of them

Every case prints what it measured and returns whether the defect reproduced.
A case that cannot reach a verdict says so and exits non-zero rather than
claiming one. That rule is here because an earlier version of one of these
scripts printed REPRODUCED after both of its test cases had crashed on a
missing import, which is the same defect the repository is about.

Some cases fetch a source file from GitHub so they execute the shipped code
rather than a retyped copy. Those need network. They say so when they fail.
"""

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).parent
CASES_DIR = ROOT / "cases"


def load(name):
    path = CASES_DIR / name / "repro.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("case_" + name.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def case_names():
    return sorted(p.name for p in CASES_DIR.iterdir()
                  if p.is_dir() and (p / "repro.py").exists())


def run_one(name):
    mod = load(name)
    if mod is None:
        print("no such case: %s" % name)
        return 2
    print("=" * 72)
    print(mod.TITLE)
    print(mod.UPSTREAM)
    print("=" * 72)
    try:
        reproduced = mod.run()
    except Exception as exc:
        print()
        print("INCONCLUSIVE: the reproduction did not run to a verdict.")
        print("  %s: %s" % (type(exc).__name__, exc))
        print("Nothing was measured, so nothing is claimed.")
        return 2
    print()
    print("REPRODUCED" if reproduced else "NOT REPRODUCED")
    return 0 if reproduced else 1


def main(argv):
    args = argv[1:]
    if not args:
        print(__doc__.strip())
        print("\ncases:")
        for name in case_names():
            mod = load(name)
            print("  %-20s %s" % (name, mod.TITLE if mod else ""))
        return 0

    if args[0] == "--all":
        results = {}
        for name in case_names():
            results[name] = run_one(name)
            print()
        print("=" * 72)
        print("summary")
        print("=" * 72)
        for name, code in results.items():
            label = {0: "reproduced", 1: "did not reproduce", 2: "INCONCLUSIVE"}[code]
            print("  %-20s %s" % (name, label))
        inconclusive = sum(1 for c in results.values() if c == 2)
        if inconclusive:
            print("\n%d case(s) could not be measured. Their status is unknown,"
                  % inconclusive)
            print("not clean.")
            return 2
        return 0 if all(c == 0 for c in results.values()) else 1

    return run_one(args[0])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
