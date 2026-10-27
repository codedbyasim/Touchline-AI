import pytest


@pytest.fixture(autouse=True)
def _no_aiml_key(monkeypatch):
    monkeypatch.delenv("AIML_API_KEY", raising=False)
