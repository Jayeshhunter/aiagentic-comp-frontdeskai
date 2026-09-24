"""Span kinds: Tempo's service graph draws an edge only from CLIENT/SERVER spans."""
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import SpanKind

import observability


def test_llm_call_is_a_client_span_to_the_provider(monkeypatch):
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(observability, "_tracer", provider.get_tracer("test"))
    monkeypatch.setenv("LLM_PROVIDER", "litellm")

    with observability.trace_llm_call("supervisor"):
        pass

    (span,) = exporter.get_finished_spans()
    assert span.name == "llm.supervisor"
    assert span.kind == SpanKind.CLIENT
    assert span.attributes["peer.service"] == "litellm"
