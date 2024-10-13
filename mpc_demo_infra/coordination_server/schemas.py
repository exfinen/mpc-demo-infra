from pydantic import BaseModel


class RequestSharingDataRequest(BaseModel):
    identity: str
    tlsn_proof: str

class RequestSharingDataResponse(BaseModel):
    mpc_port_base: int
    client_port: int
    client_id: int

class RegisterDataProviderRequest(BaseModel):
    identity: str
    voucher_code: str

class RegisterDataProviderResponse(BaseModel):
    provider_id: int
