from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .schemas import (
    NegotiateShareDataResponse, RegisterDataProviderRequest, RegisterDataProviderResponse,
    VerifyRegistrationRequest, VerifyRegistrationResponse,
)
from .database import DataProvider, Voucher, get_db

router = APIRouter()


@router.post("/register", response_model=RegisterDataProviderResponse)
def register(request: RegisterDataProviderRequest, db: Session = Depends(get_db)):

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

    return {"provider_id": new_provider.id}


@router.post("/verify_registration", status_code=status.HTTP_204_NO_CONTENT)
def verify_registration(request: VerifyRegistrationRequest, db: Session = Depends(get_db)):
    # Check if identity has not registered, raise error
    if not db.query(DataProvider).filter(DataProvider.identity == request.identity).first():
        raise HTTPException(status_code=400, detail="Identity not registered")

    # TODO: more checks
