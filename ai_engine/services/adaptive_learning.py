from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_FEEDBACK_PATH = Path(__file__).parent.parent / "calibration" / "query_feedback.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_event(event: dict[str, Any]) -> None:
    _FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _FEEDBACK_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def record_search_event(
    query: str,
    effective_query: str,
    query_domain: str | None,
    query_confidence: float,
    result_count: int,
    top_content_ids: list[str],
) -> None:
    try:
        _append_event(
            {
                "timestamp": _now_iso(),
                "event_type": "search",
                "query": query,
                "effective_query": effective_query,
                "query_domain": query_domain,
                "query_confidence": round(float(query_confidence), 4),
                "result_count": int(result_count),
                "top_content_ids": top_content_ids[:5],
            }
        )
    except Exception as exc:
        logger.debug("No se pudo registrar search event: %s", exc)


def record_feedback_event(
    event_type: str,
    query: str,
    content_id: str | None = None,
    corrected_query: str | None = None,
    notes: str | None = None,
) -> None:
    """
    event_type recomendado: click | query_correction | dislike | reclassify_suggestion
    """
    try:
        _append_event(
            {
                "timestamp": _now_iso(),
                "event_type": event_type,
                "query": query,
                "content_id": content_id,
                "corrected_query": corrected_query,
                "notes": notes,
            }
        )
    except Exception as exc:
        logger.debug("No se pudo registrar feedback event: %s", exc)
