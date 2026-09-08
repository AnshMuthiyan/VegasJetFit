"""Focused policy tests for the generic dynamic dispatcher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


DISPATCHER = Path(__file__).parents[1] / "scripts" / "dynamic_dispatch_campaign.py"
SPEC = importlib.util.spec_from_file_location("dynamic_dispatch_campaign", DISPATCHER)
assert SPEC and SPEC.loader
dispatch = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = dispatch
SPEC.loader.exec_module(dispatch)


def write_records(tmp_path: Path, event: str, record: dict) -> Path:
    path = tmp_path / "records.json"
    path.write_text(json.dumps({"events": {event: record}}))
    return path


def test_lyra_only_requires_observed_memory_evidence(tmp_path: Path) -> None:
    path = write_records(tmp_path, "test", {"host_constraint": "lyra_only"})
    with pytest.raises(ValueError, match="missing memory_evidence"):
        dispatch.read_decision_records(path, ["test"])


def test_lyra_only_accepts_documented_host_incident(tmp_path: Path) -> None:
    path = write_records(
        tmp_path,
        "test",
        {
            "host_constraint": "lyra_only",
            "memory_evidence": {
                "basis": "host_memory_incident",
                "host": "pcrc-mac-studio-2",
                "workers": 15,
                "summary": "Compressor saturated and swap grew during the warm pool.",
            },
        },
    )
    assert dispatch.read_decision_records(path, ["test"])["test"]["host_constraint"] == "lyra_only"


def test_pcrc_only_remains_a_duration_constraint_without_memory_evidence(tmp_path: Path) -> None:
    path = write_records(tmp_path, "test", {"host_constraint": "pcrc_only"})
    assert dispatch.read_decision_records(path, ["test"])["test"]["host_constraint"] == "pcrc_only"


def test_cli_lyra_only_cannot_bypass_the_evidence_requirement() -> None:
    with pytest.raises(ValueError, match="missing memory_evidence"):
        dispatch.validate_lyra_only_evidence({"test": {"host_constraint": "lyra_only"}}, {"test"})


def test_academic_year_defaults_do_not_depend_on_pcrc() -> None:
    machines = dispatch.parse_machines(dispatch.DEFAULT_MACHINES)
    assert machines[:3] == [
        ("pauley404-01", 8),
        ("pauley404-02", 8),
        ("pauley404-03", 8),
    ]
    assert ("pcrc-mac-studio-1", 14) in machines
    assert ("pcrc-mac-studio-2", 14) in machines
    assert dispatch.DEFAULT_EVENT_HOST_CONSTRAINTS == {}


def test_sync_timeout_is_isolated_to_the_failed_host(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "input.txt"
    source.write_text("science")

    def fake_run(cmd: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        host = cmd[len(dispatch.SSH_OPTS) + 1] if cmd[0] == "ssh" else cmd[-1].split(":", 1)[0]
        if host == "offline-host":
            raise subprocess.TimeoutExpired(cmd, 20)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(dispatch, "run", fake_run)
    assert dispatch.sync_to_hosts([source], ["good-host", "offline-host"]) == {"good-host"}
