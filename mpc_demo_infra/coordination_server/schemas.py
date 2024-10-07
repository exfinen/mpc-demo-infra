from pydantic import BaseModel
from typing import Optional
from enum import Enum


class MPCStatus(Enum):
    INITIAL = "INITIAL"
    WAITING_FOR_ALL_PARTIES = "WAITING_FOR_ALL_PARTIES"
    MPC_IN_PROGRESS = "MPC_IN_PROGRESS"


class VerifyIdentityRequest(BaseModel):
    identity: str

class VerifyIdentityResponse(BaseModel):
    status: str

class GetClientIdRequest(BaseModel):
    identity: str

class GetClientIdResponse(BaseModel):
    client_id: int

class NegotiateShareDataRequest(BaseModel):
    party_id: int
    identity: str

class NegotiateShareDataResponse(BaseModel):
    port: int
    status: str

class CheckShareDataStatusResponse(BaseModel):
    status: str

class NegotiateQueryComputationRequest(BaseModel):
    computation_index: int

class NegotiateQueryComputationResponse(BaseModel):
    port: int
    client_id: str

class SetShareDataCompleteRequest(BaseModel):
    party_id: int
    identity: str

class RegisterDataProviderRequest(BaseModel):
    identity: str
    voucher_code: str

class RegisterDataProviderResponse(BaseModel):
    provider_id: int

class VerifyRegistrationRequest(BaseModel):
    identity: str

class VerifyRegistrationResponse(BaseModel):
    client_id: int