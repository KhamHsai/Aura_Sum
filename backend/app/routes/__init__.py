from app.routes.auth import router as auth_router
from app.routes.health import router as health_router
from app.routes.categories import router as categories_router
from app.routes.receipts import router as receipts_router

__all__ = [
    "auth_router",
    "health_router",
    "categories_router",
    "receipts_router",
]

