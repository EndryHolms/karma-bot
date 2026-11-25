from __future__ import annotations

import asyncio
import ctypes
import gc
import logging
from typing import Any


GEMINI_TIMEOUT_SECONDS = 30
_gemini_semaphore = asyncio.Semaphore(1)
_MAX_PENDING_REQUESTS = 8
_pending_requests = 0
_MEMORY_PRESSURE_LIMIT_MB = 430.0
_fallback_models: dict[int, Any] = {}


def register_fallback_model(primary_model: Any, fallback_model: Any | None) -> None:
    if primary_model is None or fallback_model is None or fallback_model is primary_model:
        return
    _fallback_models[id(primary_model)] = fallback_model


def rss_mb() -> float | None:
    try:
        with open("/proc/self/status", "r", encoding="utf-8") as status:
            for line in status:
                if line.startswith("VmRSS:"):
                    kib = int(line.split()[1])
                    return kib / 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def release_unused_memory() -> tuple[float | None, float | None]:
    before = rss_mb()
    gc.collect()
    try:
        ctypes.CDLL(None).malloc_trim(0)
    except (AttributeError, OSError, TypeError):
        pass
    return before, rss_mb()


def _format_rss(value: float | None) -> str:
    return f"{value:.1f}" if value is not None else "unknown"


async def memory_maintenance() -> None:
    while True:
        await asyncio.sleep(60 * 60)
        before, after = await asyncio.to_thread(release_unused_memory)
        logging.info(
            "MEMORY_MAINTENANCE rss_before_mb=%s rss_after_mb=%s",
            _format_rss(before),
            _format_rss(after),
        )


async def _run_model_call(
    model: Any,
    content: Any,
    request_options: dict[str, Any],
    kwargs: dict[str, Any],
) -> Any:
    model_name = getattr(model, "model_name", type(model).__name__)
    current_rss = rss_mb()
    if current_rss is not None and current_rss >= _MEMORY_PRESSURE_LIMIT_MB:
        before, after = await asyncio.to_thread(release_unused_memory)
        logging.warning(
            "MEMORY_PRESSURE_BEFORE_GEMINI model=%s rss_before_mb=%s rss_after_mb=%s",
            model_name,
            _format_rss(before),
            _format_rss(after),
        )
        if after is not None and after >= _MEMORY_PRESSURE_LIMIT_MB:
            raise RuntimeError("Gemini skipped due to high memory pressure")

    logging.info("GEMINI_REQUEST_STARTED model=%s rss_mb=%s", model_name, _format_rss(rss_mb()))
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(
                model.generate_content,
                content,
                request_options=request_options,
                **kwargs,
            ),
            timeout=GEMINI_TIMEOUT_SECONDS + 5,
        )
    except asyncio.TimeoutError:
        logging.error("GEMINI_REQUEST_TIMEOUT model=%s", model_name)
        raise
    finally:
        before, after = await asyncio.to_thread(release_unused_memory)
        logging.info(
            "GEMINI_REQUEST_FINISHED model=%s rss_before_trim_mb=%s rss_after_trim_mb=%s",
            model_name,
            _format_rss(before),
            _format_rss(after),
        )


async def generate_content(
    model: Any,
    content: Any,
    *,
    allow_fallback: bool = True,
    **kwargs: Any,
) -> Any:
    """Run one bounded Gemini request at a time on the small Render instance."""
    global _pending_requests
    if _pending_requests >= _MAX_PENDING_REQUESTS:
        logging.warning("GEMINI_QUEUE_FULL pending=%s", _pending_requests)
        raise RuntimeError("Gemini request queue is full")
    _pending_requests += 1

    request_options = dict(kwargs.pop("request_options", {}) or {})
    request_options.setdefault("timeout", GEMINI_TIMEOUT_SECONDS)

    try:
        async with _gemini_semaphore:
            try:
                return await _run_model_call(model, content, dict(request_options), kwargs)
            except Exception as exc:
                fallback = _fallback_models.get(id(model)) if allow_fallback else None
                if fallback is None:
                    raise
                logging.warning(
                    "GEMINI_FALLBACK_TRIGGERED primary=%s fallback=%s error_type=%s error=%s",
                    getattr(model, "model_name", type(model).__name__),
                    getattr(fallback, "model_name", type(fallback).__name__),
                    type(exc).__name__,
                    exc,
                )
                return await _run_model_call(fallback, content, dict(request_options), kwargs)
    finally:
        _pending_requests -= 1
