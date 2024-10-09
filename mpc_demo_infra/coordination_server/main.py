from fastapi import FastAPI
from .routes import router
from .middleware import IPFilterMiddleware
from .database import engine, Base
from .config import settings
from fastapi.middleware.cors import CORSMiddleware
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("coordination_server")

app = FastAPI(
    title="Coordination Server",
    description="API for MPC Coordination",
    version="1.0.0",
)

# Create database tables
Base.metadata.create_all(bind=engine)

# CORS Middleware (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add IP Filtering Middleware
# app.add_middleware(IPFilterMiddleware)

# Add API Key Middleware (optional)
# Uncomment the next line to enable API Key authentication
# app.add_middleware(APIKeyMiddleware)

# Include API routes
app.include_router(router)

# Event handlers
@app.on_event("startup")
async def startup_event():
    logger.info("Coordination Server is starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Coordination Server is shutting down...")

# Custom exception handlers can be added here

def run():
    import uvicorn
    uvicorn.run(
        "mpc_demo_infra.coordination_server.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=True
    )
