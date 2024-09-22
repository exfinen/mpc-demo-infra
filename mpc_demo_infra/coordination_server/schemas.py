from pydantic import BaseModel
from typing import Optional

class VerifyIdentityRequest(BaseModel):
    identity: str

class VerifyIdentityResponse(BaseModel):
    status: str

class NegotiateShareDataRequest(BaseModel):
    # Define any required fields if needed
    pass

class NegotiateShareDataResponse(BaseModel):
    port: int
    client_id: str

class NegotiateQueryComputationRequest(BaseModel):
    computation_index: int

class NegotiateQueryComputationResponse(BaseModel):
    port: int
    client_id: str

class SuccessRequest(BaseModel):
    client_id: str

class SuccessResponse(BaseModel):
    status: str

class RegisterDataProviderRequest(BaseModel):
    voucher_code: str

class RegisterDataProviderResponse(BaseModel):
    provider_id: int
