from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .schemas import NegotiateShareDataResponse, RegisterDataProviderRequest, RegisterDataProviderResponse
from .database import DataProvider, Voucher, get_db
import uuid

router = APIRouter()


@router.post("/register", response_model=RegisterDataProviderResponse)
def register(request: RegisterDataProviderRequest, db: Session = Depends(get_db)):
    print(f"Register endpoint called with voucher code: {request.voucher_code}")

    voucher: Voucher | None = db.query(Voucher).filter(Voucher.code == request.voucher_code).first()
    print(f"Found voucher: {voucher}")

    if not voucher:
        raise HTTPException(status_code=400, detail="Invalid voucher code")
    if voucher.data_provider:
        raise HTTPException(status_code=400, detail="Voucher already used")

    # Create a new data provider and associate it with the voucher
    new_provider = DataProvider(voucher=voucher)
    db.add(new_provider)
    db.commit()
    db.refresh(new_provider)

    return {"provider_id": new_provider.id}


@router.post("/negotiate_share_data", response_model=NegotiateShareDataResponse)
def negotiate_share_data(db: Session = Depends(get_db)):
    client_id = str(uuid.uuid4())
    port = 8000 + (len(db.query(Client).all()) % 1000)
    client = Client(client_id=client_id, port=port)
    db.add(client)
    db.commit()
    db.refresh(client)
    return {"port": client.port, "client_id": client.client_id}

