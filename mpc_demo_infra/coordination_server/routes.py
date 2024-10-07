import time
from dataclasses import dataclass
import logging
from threading import Lock, Event

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from .schemas import (
    NegotiateShareDataRequest, NegotiateShareDataResponse,
    RegisterDataProviderRequest, RegisterDataProviderResponse,
    VerifyRegistrationRequest, VerifyRegistrationResponse,
    MPCStatus, CheckShareDataStatusResponse,
    SetShareDataCompleteRequest,
)
from .database import DataProvider, Voucher, get_db
from .config import settings

router = APIRouter()

#
# Public APIs
#

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


#
# Party Server APIs: callable by parties
#

@dataclass(frozen=True)
class Session:
    identity: str
    time: int

# Global lock and session tracking
global_lock = Lock()
indicated_joining_mpc: dict[int, Session] = {}
indicated_mpc_complete: dict[int, Session] = {}


@router.post("/negotiate_share_data", response_model=NegotiateShareDataResponse)
def negotiate_share_data(request: NegotiateShareDataRequest, db: Session = Depends(get_db)):
    party_id = request.party_id
    identity = request.identity
    logger.info(f"Negotiating share data for {party_id=} from {identity=}")

    with global_lock:
        state = get_current_state()
        if state == MPCStatus.MPC_IN_PROGRESS:
            logger.error(f"Cannot negotiate share data: MPC is in progress. Current state: {state}")
            raise HTTPException(status_code=400, detail="Cannot negotiate share data: MPC is in progress")
        if party_id in indicated_joining_mpc:
            logger.error(f"Party {party_id} already waiting for MPC")
            raise HTTPException(status_code=400, detail="Party already waiting")
        # Check if every party is running for the same identity
        if any(indicated_joining_mpc[id].identity != identity for id in indicated_joining_mpc):
            logger.error(f"Party {party_id} is running for different identity")
            raise HTTPException(status_code=400, detail="Party is running for different identity")
        # Add the party to the indicated joining MPC for the given identity
        indicated_joining_mpc[party_id] = Session(identity=identity, time=time.time())
        logger.info(f"Party {party_id} joined MPC. Total parties: {len(indicated_joining_mpc)}")
        current_state = get_current_state()
        if current_state == MPCStatus.MPC_IN_PROGRESS:
            logger.info("All parties joined. MPC is now in progress.")
        elif current_state == MPCStatus.WAITING_FOR_ALL_PARTIES:
            logger.info(f"Waiting for more parties. Current count: {len(indicated_joining_mpc)}, required: {settings.num_parties}")
        else:
            raise HTTPException(status_code=400, detail=f"Invalid state: {current_state}")
        return NegotiateShareDataResponse(
            port=settings.mpc_port,
            status=current_state.value,
        )


@router.post("/set_share_data_complete", status_code=status.HTTP_204_NO_CONTENT)
def set_share_data_complete(request: SetShareDataCompleteRequest):
    party_id = request.party_id
    identity = request.identity
    logger.info(f"Setting share data complete for {party_id=}")
    with global_lock:
        state = get_current_state()
        if state != MPCStatus.MPC_IN_PROGRESS:
            logger.error(f"Cannot set share data complete: MPC is not in progress. Current state: {state}")
            raise HTTPException(status_code=400, detail="Cannot set share data complete: MPC is not in progress")
        if party_id not in indicated_joining_mpc:
            logger.error(f"Party {party_id} not waiting in MPC")
            raise HTTPException(status_code=400, detail="Party not waiting")
        # Check if every party is running for the same identity
        if any(indicated_mpc_complete[id].identity != identity for id in indicated_mpc_complete):
            logger.error(f"Party {party_id} is running for different identity")
            raise HTTPException(status_code=400, detail="Party is running for different identity")
        indicated_mpc_complete[party_id] = Session(identity=identity, time=time.time())
        logger.info(f"Party {party_id} completed MPC. Total completed: {len(indicated_mpc_complete)}")
        if len(indicated_mpc_complete) == settings.num_parties:
            logger.info("All parties completed MPC. Cleaning up states.")
            cleanup_states()


@router.get("/check_share_data_status", response_model=CheckShareDataStatusResponse)
def check_share_data_status():
    logger.info("Checking share data status")
    with global_lock:
        state = get_current_state()
    logger.info(f"Current share data status: {state}")
    return {"status": state.value}


#
# Admin APIs: callable by admin
#

@router.post("/cleanup_sessions", status_code=status.HTTP_204_NO_CONTENT)
def cleanup_sessions():
    logger.info("Cleaning up stale sessions")
    with global_lock:
        cleanup_states()
    logger.info("Stale sessions cleaned up")



def get_current_state() -> MPCStatus:
    # no lock is acquired here, the caller should acquire the lock
    num_parties_indicated_joining = len(indicated_joining_mpc)
    num_parties_indicated_complete = len(indicated_mpc_complete)
    logger.debug(f"Current state: Parties joined: {num_parties_indicated_joining}, Parties completed: {num_parties_indicated_complete}")

    # initial: both num_parties_indicated_complete and num_parties_indicated_joining are 0
    # waiting for all parties: num_parties_indicated_joining == settings.num_parties, num_parties_indicated_complete == 0
    # mpc in progress: num_parties_indicated_joining == settings.num_parties
    if num_parties_indicated_joining == 0:
        if num_parties_indicated_complete != 0:
            raise HTTPException(status_code=400, detail="Invalid state: should be no one indicating complete when no one has joined")
        return MPCStatus.INITIAL
    elif num_parties_indicated_joining < settings.num_parties:
        if num_parties_indicated_complete > 0:
            raise HTTPException(status_code=400, detail="Invalid state: should be no one indicating complete when not all parties have joined")
        return MPCStatus.WAITING_FOR_ALL_PARTIES
    elif num_parties_indicated_joining == settings.num_parties:
        return MPCStatus.MPC_IN_PROGRESS
    else:
        raise HTTPException(status_code=400, detail=f"Invalid state: num_parties_indicated_joining = {num_parties_indicated_joining}, num_parties_indicated_complete = {num_parties_indicated_complete}")


def cleanup_states():
    logger.info("Cleaning up MPC states")
    indicated_joining_mpc.clear()
    indicated_mpc_complete.clear()
    logger.info("MPC states cleaned up")
