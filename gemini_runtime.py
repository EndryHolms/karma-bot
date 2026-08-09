from __future__ import annotations

import asyncio
import logging
from typing import Any


GEMINI_TIMEOUT_SECONDS = 60
_gemini_semaphore = asyncio.Semaphore(1)
_MAX_PENDING_REQUESTS = 8
_pending_requests = 0


def _rss_mb() -> str:
    try:
        with open("/proc/self/status", "r", encoding="utf-8") as status:
            for line in status:
                if line.startswith("VmRSS:"):
                    kib = int(line.split()[1])
                    return f"{kib / 1024:.1f}"
    except (OSError, ValueError, IndexError):
        pass
    return "unknown"


async def generate_content(model: Any, content: Any, **kwargs: Any) -> Any:
    """Run one bounded Gemini request at a time on the small Render instance."""
    global _pending_requests
    if _pending_requests >= _MAX_PENDING_REQUESTS:
        logging.warning("GEMINI_QUEUE_FULL pending=%s", _pending_requests)
        raise RuntimeError("Gemini request queue is full")
    _pending_requests += 1

    request_options = dict(kwargs.pop("request_options", {}) or {})
    request_options.setdefault("timeout", GEMINI_TIMEOUT_SECONDS)
    model_name = getattr(model, "model_name", type(model).__name__)

    try:
        async with _gemini_semaphore:
            logging.info("GEMINI_REQUEST_STARTED model=%s rss_mb=%s", model_name, _rss_mb())
            try:
                response = await asyncio.wait_for(
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
                logging.info("GEMINI_REQUEST_FINISHED model=%s rss_mb=%s", model_name, _rss_mb())
    finally:
        _pending_requests -= 1

    return response
