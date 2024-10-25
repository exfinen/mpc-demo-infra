import argparse
import csv
import logging
import secrets
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .routes import router
from .middleware import IPFilterMiddleware
from .database import engine, Base, SessionLocal, Voucher
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

logger = logging.getLogger("coordination_server")

app = FastAPI(
    title="Coordination Server",
    description="API for MPC Coordination",
    version="1.0.0",
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Set up limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
    print(f"Running coordination server on port {settings.port}")
    uvicorn.run(
        "mpc_demo_infra.coordination_server.main:app",
        host="0.0.0.0",
        port=settings.port,
        log_level="debug"
    )


def gen_vouchers():
    parser = argparse.ArgumentParser(description="Generate vouchers for the MPC Coordination Server")
    parser.add_argument("num_vouchers", type=int, help="Number of vouchers to generate")
    args = parser.parse_args()

    num_vouchers = int(args.num_vouchers)

    print(f"Generating {num_vouchers} vouchers...")

    vouchers = [secrets.token_urlsafe(16) for _ in range(num_vouchers)]
    with SessionLocal() as db:
        for voucher_code in vouchers:
            while True:
                new_voucher = Voucher(code=voucher_code)
                if not str(new_voucher).startswith('-'):
                    db.add(new_voucher)
                    break
        db.commit()  # Add this line to commit the changes
    print(f"Successfully generated and committed {num_vouchers} vouchers.")
    print(f"Generated vouchers:")
    for voucher in vouchers:
        print(voucher)


def list_vouchers():
    writer = csv.writer(sys.stdout)
    writer.writerow(["id", "voucher_code", "is_used"])
    with SessionLocal() as db:
        vouchers = db.query(Voucher).all()
        for voucher in vouchers:
            writer.writerow([voucher.id, voucher.code, voucher.is_used])


def gen_party_api_key():
    print(secrets.token_hex(16))
