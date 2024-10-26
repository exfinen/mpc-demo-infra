import logging
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from .routes import router
from .config import settings
from .limiter import limiter

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("data_consumer_api")

app = FastAPI(
    title="Data Consumer API Server",
    description="A simple API server querying computations for data consumers, and thus can be called by browsers",
    version="1.0.0",
)


# Set up limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Include API routes
app.include_router(router)

# Event handlers
@app.on_event("startup")
async def startup_event():
    logger.info("Data Consumer API Server is starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Data Consumer API Server is shutting down...")

# Custom exception handlers can be added here

def run():
    import uvicorn
    print(f"Running data consumer API server on port {settings.port}")
    uvicorn.run(
        "mpc_demo_infra.data_consumer_api.main:app",
        host="0.0.0.0",
        port=settings.port,
        log_level="debug"
    )
