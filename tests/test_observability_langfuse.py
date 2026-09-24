"""Langfuse trace tags: a shared project must still tell namespaces apart."""
from observability import langfuse_tags


def test_tag_is_the_tracing_environment(monkeypatch):
    monkeypatch.setenv("LANGFUSE_TRACING_ENVIRONMENT", "agenticaiu5")
    assert langfuse_tags() == ["agenticaiu5"]


def test_no_tag_when_unset(monkeypatch):
    monkeypatch.delenv("LANGFUSE_TRACING_ENVIRONMENT", raising=False)
    assert langfuse_tags() == []
