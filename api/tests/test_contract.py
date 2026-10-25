"""El código implementa exactamente las operaciones del contrato api/openapi.yaml."""

from pathlib import Path

import yaml
from fastapi.testclient import TestClient

CONTRACT = Path(__file__).resolve().parents[1] / "openapi.yaml"
METHODS = {"get", "post", "put", "patch", "delete"}


def operations(paths: dict) -> set[tuple[str, str]]:
    return {(m, p) for p, ops in paths.items() for m in ops if m in METHODS}


def test_implementation_matches_contract(client: TestClient) -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    implemented = client.get("/openapi.json").json()["paths"]
    expected = operations(contract["paths"])
    actual = {op for op in operations(implemented) if op[1] != "/health"}
    assert expected == actual
