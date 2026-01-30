from .start import router as start_router
from .tarot import router as tarot_router
from .advice import router as advice_router
from .payment import router as payment_router

__all__ = [
    "start_router",
    "tarot_router",
    "advice_router",
    "payment_router",
]
