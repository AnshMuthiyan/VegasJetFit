# Ethan Setup Guide (VegasJetFit + Vendored VegasAfterglow)

This is the shortest reliable path to run the current GRB workflow on a Mac.

## 1) Pull the Repository

```bash
git clone git@github.com:AnshMuthiyan/VegasJetFit.git
cd VegasJetFit
```

## 2) Create a Fresh Python Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

## 3) Install the Vendored VegasAfterglow Engine

```bash
./scripts/setup_vendored_vegasafterglow.sh
```

This script must print:

- Python executable
- VegasAfterglow import path
- VegasAfterglow version
- `Vendored import verification: OK`

If the import path is not inside:

```text
VegasJetFit/external/VegasAfterglow/VegasAfterglow/__init__.py
```

stop and fix environment/path issues before running fits.

## 4) Smoke Test

From the repo root:

```bash
PYTHONPATH=$PWD python scripts/noop_status.py
```

Then run one small preflight/smoke fitting command used by current workflow.

## 5) Important Rule

Do not replace vendored VegasAfterglow with arbitrary pip/upstream builds for this campaign unless we explicitly revalidate all affected outputs.

## Reference Docs

- `REPRODUCIBILITY.md`
- `external/VegasAfterglow/README_LOCAL.md`

