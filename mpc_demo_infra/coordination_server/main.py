import argparse
import csv
import logging
import secrets
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router
from .middleware import IPFilterMiddleware
from .database import engine, Base, SessionLocal, Voucher
from .config import settings


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
    print(f"Running coordination server on port {settings.port}")
    uvicorn.run(
        "mpc_demo_infra.coordination_server.main:app",
        host="0.0.0.0",
        port=settings.port,
        # reload=True
    )


def gen_vouchers():
    parser = argparse.ArgumentParser(description="Generate vouchers for the MPC Coordination Server")
    parser.add_argument("num_vouchers", type=int, help="Number of vouchers to generate")
    args = parser.parse_args()

    num_vouchers = int(args.num_vouchers)

    print(f"Generating {num_vouchers} vouchers...")

    with SessionLocal() as db:
        for _ in range(num_vouchers):
            voucher_code = secrets.token_urlsafe(16)
            new_voucher = Voucher(code=voucher_code)
            db.add(new_voucher)
        db.commit()  # Add this line to commit the changes
        print(f"Successfully generated and committed {num_vouchers} vouchers.")


def list_vouchers():
    writer = csv.writer(sys.stdout)
    writer.writerow(["id", "voucher_code", "is_used"])
    with SessionLocal() as db:
        vouchers = db.query(Voucher).all()
        for voucher in vouchers:
            writer.writerow([voucher.id, voucher.code, voucher.is_used])
