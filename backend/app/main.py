from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth_router, health_router, categories_router, receipts_router, expenses_router
from app.config import settings

app = FastAPI(
    title="Smart Receipt API",
    version="1.0.0"
)

# Build the list of allowed origins for CORS.
# Always include the Vite dev server origins.
# Also include FRONTEND_URL from .env when it is set.
_cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
if settings.FRONTEND_URL:
    _cors_origins.append(settings.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(categories_router)
app.include_router(receipts_router)
app.include_router(expenses_router)

