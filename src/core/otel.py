"""OpenTelemetry configuration and instrumentation."""

import logging

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.core.config import config


def setup_otel(app: FastAPI | None = None) -> None:
    """Sets up OpenTelemetry tracing and instrumentation.

    Args:
        app: Optional FastAPI application instance to instrument.
    """
    # Define the service resource
    resource = Resource(
        attributes={
            SERVICE_NAME: 'nexusedu',
        }
    )

    # Initialize TracerProvider
    provider = TracerProvider(resource=resource)

    # Use the default OTLPSpanExporter. It automatically respects standard OTel
    # environment variables like OTEL_EXPORTER_OTLP_ENDPOINT.
    exporter = OTLPSpanExporter()

    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    # Instrument FastAPI if app is provided
    if app:
        FastAPIInstrumentor.instrument_app(app)

    # Instrument Database (Psycopg)
    PsycopgInstrumentor().instrument()

    # Instrument Redis
    RedisInstrumentor().instrument()

    logging.info('OpenTelemetry instrumentation completed.')
