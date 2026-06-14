from fastapi import FastAPI
from app.routes import auth_router, health_router

app = FastAPI(
    title="Smart Receipt API",
    version="1.0.0"
)

# Register routes
app.include_router(health_router)
app.include_router(auth_router)
