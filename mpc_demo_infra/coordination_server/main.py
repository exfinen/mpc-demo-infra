import argparse
import csv
import logging
import secrets
import sys

from fastapi import FastAPI
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .routes import router
from .database import engine, Base, SessionLocal, MPCSession
from .config import settings
from .limiter import limiter
from .user_queue import UserQueue
from contextlib import asynccontextmanager
from ..logger_config import configure_file_console_loggers

configure_file_console_loggers(
    'coord',
    max_bytes_mb=settings.max_bytes_mb,
    backup_count=settings.backup_count
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.user_queue = UserQueue(settings.user_queue_size, settings.user_queue_head_timeout)
    yield
    logger.info("shutting down")

app = FastAPI(
    title="Coordination Server",
    description="API for MPC Coordination",
    version="1.0.0",
    lifespan=lifespan,
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Set up limiter
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# app.add_middleware(SlowAPIMiddleware)
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
    logger.info(f"Running coordination server on port {settings.port} with settings: {settings}")
    if settings.party_web_protocol == 'https':
        uvicorn.run(
            "mpc_demo_infra.coordination_server.main:app",
            host="0.0.0.0",
            port=settings.port,
            ssl_keyfile=settings.privkey_pem_path,
            ssl_certfile=settings.fullchain_pem_path,
            log_level="debug"
        )
    else:
        uvicorn.run(
            "mpc_demo_infra.coordination_server.main:app",
            host="0.0.0.0",
            port=settings.port,
            log_level="debug"
        )


def list_mpc_sessions():
    writer = csv.writer(sys.stdout)
    with SessionLocal() as db:
        mpc_sessions = db.query(MPCSession).all()
        number_of_sessions = len(mpc_sessions)
        logger.info(f"Number of MPC sessions: {number_of_sessions}")
        writer.writerow(["id", "eth_address", "uid", "tlsn_proof_path"])
        for mpc_session in mpc_sessions:
            writer.writerow([mpc_session.id, mpc_session.eth_address, mpc_session.uid, mpc_session.tlsn_proof_path])


def gen_party_api_key():
    print(secrets.token_hex(16))
