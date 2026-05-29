#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDORED_DIR="$REPO_ROOT/external/VegasAfterglow"
EXPECTED_INIT="$VENDORED_DIR/VegasAfterglow/__init__.py"

if [[ ! -d "$VENDORED_DIR" ]]; then
  echo "ERROR: vendored VegasAfterglow directory not found: $VENDORED_DIR" >&2
  exit 1
fi

if [[ "${1:-}" == "--python" ]]; then
  PYTHON_BIN="$2"
else
  if [[ -x "/Users/jkeohane/GRBs/.venv/bin/python" ]]; then
    PYTHON_BIN="/Users/jkeohane/GRBs/.venv/bin/python"
  else
    PYTHON_BIN="$(command -v python3)"
  fi
fi

if [[ -z "${PYTHON_BIN:-}" || ! -x "$PYTHON_BIN" ]]; then
  echo "ERROR: could not find executable Python interpreter." >&2
  exit 1
fi

echo "Using Python: $PYTHON_BIN"
echo "Repo root: $REPO_ROOT"
echo "Vendored VegasAfterglow: $VENDORED_DIR"

"$PYTHON_BIN" -m pip install --upgrade pip setuptools wheel >/dev/null
"$PYTHON_BIN" -m pip install -e "$VENDORED_DIR"

echo
echo "Verifying VegasAfterglow import source..."
"$PYTHON_BIN" - <<PY
import importlib.util
import pathlib
import sys

expected = pathlib.Path(r"$EXPECTED_INIT").resolve()
spec = importlib.util.find_spec("VegasAfterglow")
if spec is None or not spec.origin:
    print("ERROR: VegasAfterglow is not importable.", file=sys.stderr)
    raise SystemExit(2)
origin = pathlib.Path(spec.origin).resolve()
print(f"Python executable: {sys.executable}")
print(f"VegasAfterglow import path: {origin}")
if origin != expected:
    print("ERROR: VegasAfterglow import path does not match vendored source.", file=sys.stderr)
    print(f"Expected: {expected}", file=sys.stderr)
    raise SystemExit(3)

import VegasAfterglow as va
print(f"VegasAfterglow version: {getattr(va, '__version__', 'UNKNOWN')}")
print("Vendored import verification: OK")
PY

echo
echo "setup_vendored_vegasafterglow.sh complete."

