import time
import logging
from threading import Lock, Event

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from .schemas import (
    NegotiateShareDataRequest, NegotiateShareDataResponse,
    RegisterDataProviderRequest, RegisterDataProviderResponse,
    VerifyRegistrationRequest, VerifyRegistrationResponse,
    GetClientIdRequest, GetClientIdResponse, MPCStatus, CheckShareDataStatusResponse,
    SetShareDataCompleteRequest, SetShareDataCompleteResponse,
)
from .database import DataProvider, Voucher, get_db
from .config import settings

router = APIRouter()


@router.post("/register", response_model=RegisterDataProviderResponse)
def register(request: RegisterDataProviderRequest, db: Session = Depends(get_db)):
    logger.info(f"Attempting to register provider with identity: {request.identity}")
    # Check if voucher is valid
    voucher: Voucher | None = db.query(Voucher).filter(Voucher.code == request.voucher_code).first()
    if not voucher:
        raise HTTPException(status_code=400, detail="Invalid voucher code")
    if voucher.data_provider:
        raise HTTPException(status_code=400, detail="Voucher already used")

    # Check if identity has existed, raise error
    if db.query(DataProvider).filter(DataProvider.identity == request.identity).first():
        raise HTTPException(status_code=400, detail="Identity already exists")

    # Create a new data provider and associate it with the voucher
    new_provider = DataProvider(voucher=voucher, identity=request.identity)
    db.add(new_provider)
    db.commit()
    db.refresh(new_provider)
    logger.info(f"Successfully registered provider with id: {new_provider.id}")
    return {"provider_id": new_provider.id}


@router.post("/verify_registration", response_model=VerifyRegistrationResponse)
def verify_registration(request: VerifyRegistrationRequest, db: Session = Depends(get_db)):
    logger.info(f"Verifying registration for identity: {request.identity}")
    # Check if identity has not registered, raise error
    data_provider: DataProvider | None = db.query(DataProvider).filter(DataProvider.identity == request.identity).first()
    if not data_provider:
        raise HTTPException(status_code=400, detail="Identity not registered")

    # TODO: more checks
    logger.info(f"Registration verified for identity: {request.identity}")
    return {"client_id": data_provider.id}


# SESSION_TIMEOUT = 300  # 5 minutes timeout

# Global lock and session tracking
global_lock = Lock()
indicated_joining_mpc: dict[int, int] = {}
indicated_mpc_complete: dict[int, int] = {}
is_data_sharing_in_progress = Event()


@router.post("/negotiate_share_data", response_model=NegotiateShareDataResponse)
def negotiate_share_data(request: NegotiateShareDataRequest):
    party_id = request.party_id
    logger.info(f"Negotiating share data for party {party_id}")
    # States: "INITIAL", "WAITING_FOR_ALL_PARTIES", "MPC_IN_PROGRESS"
    # 1. party_1 calls /negotiate_share_data(party_id=1). if timeout, all parties are unblocked and get error response.
    # 2. party_2 calls /negotiate_share_data(party_id=2).
    # 3. party_3 calls /negotiate_share_data(party_id=3). All parties are unblocked. lock for sharing data is held.
    # 4. party_1, party_2, party_3 run mpc
    # 5. party_1 calls /set_share_data_success(party_id=1)
    # 6. party_2 calls /set_share_data_success(party_id=2)
    # 7. party_3 calls /set_share_data_success(party_id=3)
    # 8. lock is released
    with global_lock:
        if is_data_sharing_in_progress.is_set():
            logger.info(f"Data sharing already in progress for party {party_id}")
            raise HTTPException(status_code=400, detail="Data sharing already in progress")
        if party_id in indicated_joining_mpc:
            logger.error(f"Party {party_id} already waiting for MPC")
            raise HTTPException(status_code=400, detail="Party already waiting")
        indicated_joining_mpc[party_id] = time.time()
        logger.info(f"Party {party_id} joined MPC. Total parties: {len(indicated_joining_mpc)}")
        if len(indicated_joining_mpc) == settings.num_parties:
            is_data_sharing_in_progress.set()
            logger.info("All parties joined. MPC is now in progress.")
            return NegotiateShareDataResponse(status=MPCStatus.MPC_IN_PROGRESS.value, port=settings.mpc_port)
        else:
            logger.info(f"Waiting for more parties. Current count: {len(indicated_joining_mpc)}")
            return NegotiateShareDataResponse(status=MPCStatus.WAITING_FOR_ALL_PARTIES.value, port=settings.mpc_port)


@router.post("/set_share_data_complete", status_code=status.HTTP_204_NO_CONTENT)
def set_share_data_complete(request: SetShareDataCompleteRequest):
    party_id = request.party_id
    logger.info(f"Setting share data complete for party {party_id}")
    with global_lock:
        state = get_current_state()
        if state != MPCStatus.MPC_IN_PROGRESS:
            logger.error(f"Cannot set share data complete: MPC is not in progress. Current state: {state}")
            raise HTTPException(status_code=400, detail="Cannot set share data complete: MPC is not in progress")
        if party_id not in indicated_joining_mpc:
            logger.error(f"Party {party_id} not waiting in MPC")
            raise HTTPException(status_code=400, detail="Party not waiting")
        indicated_mpc_complete[party_id] = time.time()
        logger.info(f"Party {party_id} completed MPC. Total completed: {len(indicated_mpc_complete)}")
        if len(indicated_mpc_complete) == settings.num_parties:
            logger.info("All parties completed MPC. Cleaning up states.")
            cleanup_states()


@router.post("/cleanup_sessions", status_code=status.HTTP_204_NO_CONTENT)
def cleanup_sessions():
    logger.info("Cleaning up stale sessions")
    with global_lock:
        cleanup_states()
    logger.info("Stale sessions cleaned up")


@router.get("/check_share_data_status", response_model=CheckShareDataStatusResponse)
def check_share_data_status():
    logger.info("Checking share data status")
    with global_lock:
        state = get_current_state()
    logger.info(f"Current share data status: {state}")
    return {"status": state.value}


def get_current_state() -> MPCStatus:
    num_parties_indicated_joining = len(indicated_joining_mpc)
    num_parties_indicated_complete = len(indicated_mpc_complete)
    logger.debug(f"Current state: Parties joined: {num_parties_indicated_joining}, Parties completed: {num_parties_indicated_complete}")

    if is_data_sharing_in_progress.is_set():
        if num_parties_indicated_joining != settings.num_parties:
            raise HTTPException(status_code=400, detail="Invalid state: MPC is in progress but not all parties have joined")
        return MPCStatus.MPC_IN_PROGRESS
    else:
        if num_parties_indicated_complete > 0:
            raise HTTPException(status_code=400, detail="Invalid state: parties have completed MPC but data sharing is not in progress")
        if num_parties_indicated_joining == 0:
            return MPCStatus.INITIAL
        elif num_parties_indicated_joining < settings.num_parties:
            return MPCStatus.WAITING_FOR_ALL_PARTIES
        else:
            raise HTTPException(status_code=400, detail="Invalid state: all parties have joined but MPC is not in progress")


def cleanup_states():
    logger.info("Cleaning up MPC states")
    indicated_joining_mpc.clear()
    indicated_mpc_complete.clear()
    is_data_sharing_in_progress.clear()
    logger.info("MPC states cleaned up")
