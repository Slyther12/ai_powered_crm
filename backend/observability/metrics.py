"""
Observability metrics tracking — stores pipeline metrics in SQLite
for queryability via the /api/observability endpoints.
"""
import time
from datetime import datetime, timezone
from contextlib import contextmanager

from backend.observability.logger import get_logger, log_with_extras

logger = get_logger("metrics")

# In-memory metrics buffer (flushed to DB periodically or on request)
_metrics_buffer: list[dict] = []


def record_metric(
    stage: str,
    operation: str,
    duration_ms: float = 0,
    tokens_used: int = 0,
    tokens_prompt: int = 0,
    tokens_completion: int = 0,
    error: str = None,
    metadata: dict = None,
):
    """Record a pipeline metric entry."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "operation": operation,
        "duration_ms": round(duration_ms, 2),
        "tokens_used": tokens_used,
        "tokens_prompt": tokens_prompt,
        "tokens_completion": tokens_completion,
        "error": error,
        "metadata": metadata or {},
    }
    _metrics_buffer.append(entry)
    log_with_extras(logger, "DEBUG", f"Metric recorded: {stage}/{operation}",
                    duration_ms=duration_ms, tokens=tokens_used)


@contextmanager
def measure_latency(stage: str, operation: str, **extra_metadata):
    """Context manager to measure and record latency for an operation."""
    start = time.perf_counter()
    error = None
    try:
        yield
    except Exception as e:
        error = str(e)
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        record_metric(
            stage=stage,
            operation=operation,
            duration_ms=duration_ms,
            error=error,
            metadata=extra_metadata,
        )


def get_metrics_buffer() -> list[dict]:
    """Return current metrics buffer."""
    return list(_metrics_buffer)


def flush_metrics_to_db(db_session):
    """Flush buffered metrics to the observability_log table."""
    from backend.models import ObservabilityLog
    import json

    entries = list(_metrics_buffer)
    _metrics_buffer.clear()

    for entry in entries:
        log_entry = ObservabilityLog(
            timestamp=datetime.fromisoformat(entry["timestamp"]),
            stage=entry["stage"],
            operation=entry["operation"],
            duration_ms=entry["duration_ms"],
            tokens_used=entry["tokens_used"],
            tokens_prompt=entry["tokens_prompt"],
            tokens_completion=entry["tokens_completion"],
            error=entry["error"],
            metadata_json=json.dumps(entry["metadata"]),
        )
        db_session.add(log_entry)
    db_session.commit()
    logger.info(f"Flushed {len(entries)} metrics to database")


def get_aggregate_metrics(db_session) -> dict:
    """Compute aggregate metrics from the database."""
    from backend.models import ObservabilityLog
    from sqlalchemy import func

    total_logs = db_session.query(func.count(ObservabilityLog.id)).scalar() or 0
    total_tokens = db_session.query(
        func.sum(ObservabilityLog.tokens_used)
    ).scalar() or 0
    avg_latency = db_session.query(
        func.avg(ObservabilityLog.duration_ms)
    ).filter(ObservabilityLog.duration_ms > 0).scalar() or 0
    error_count = db_session.query(
        func.count(ObservabilityLog.id)
    ).filter(ObservabilityLog.error.isnot(None)).scalar() or 0

    # Per-stage breakdown
    stage_stats = db_session.query(
        ObservabilityLog.stage,
        func.count(ObservabilityLog.id).label("count"),
        func.avg(ObservabilityLog.duration_ms).label("avg_latency_ms"),
        func.sum(ObservabilityLog.tokens_used).label("total_tokens"),
    ).group_by(ObservabilityLog.stage).all()

    return {
        "total_operations": total_logs,
        "total_tokens_used": total_tokens,
        "avg_latency_ms": round(avg_latency, 2),
        "total_errors": error_count,
        "by_stage": [
            {
                "stage": s.stage,
                "count": s.count,
                "avg_latency_ms": round(s.avg_latency_ms or 0, 2),
                "total_tokens": s.total_tokens or 0,
            }
            for s in stage_stats
        ],
    }
