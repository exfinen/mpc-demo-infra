import logging
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .routes import router
from .middleware import APIKeyMiddleware
from .limiter import limiter
from .database import engine, Base
from .config import settings


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("computation_party_server")

app = FastAPI(
    title="Computation Party Server",
    description="API for MPC Computation Party",
    version="1.0.0",
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Set up limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(APIKeyMiddleware)
# Add middlewares
# app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Include API routes
app.include_router(router)

# Event handlers
@app.on_event("startup")
async def startup_event():
    logger.info("Computation Party Server is starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Computation Party Server is shutting down...")

# Custom exception handlers can be added here

def run():
    import uvicorn
    uvicorn.run(
        "mpc_demo_infra.computation_party_server.main:app",
        host="0.0.0.0",
        port=settings.port,
        # reload=True
    )
