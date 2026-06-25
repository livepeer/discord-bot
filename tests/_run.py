"""Zero-dependency test runner (pytest is unavailable in this sandbox).

Use `python -m pytest -q` in a normal environment; this just mirrors that here.
"""
import importlib
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tests"))
sys.path.insert(0, ROOT)

passed = failed = 0
for m in ("test_formatting", "test_moderation"):
    mod = importlib.import_module(m)
    for name in sorted(dir(mod)):
        if name.startswith("test_"):
            try:
                getattr(mod, name)()
                passed += 1
                print(f"PASS {m}.{name}")
            except Exception:
                failed += 1
                print(f"FAIL {m}.{name}")
                traceback.print_exc()

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
