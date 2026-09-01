from datetime import datetime
from pydantic import BaseModel, ConfigDict

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    role: str

class LoginIn(BaseModel):
    email: str
    password: str

class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    case_number: str
    title: str
    description: str
    status: str
    priority: str
    station: str
    is_demo: bool
    created_at: datetime

class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    document_number: str
    case_id: int
    title: str
    document_type: str
    classification: str
    current_version: int
    created_at: datetime

class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    document_id: int
    version: int
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    uploaded_by: int
    created_at: datetime

class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    actor_id: int | None
    action: str
    target_type: str
    target_id: str
    result: str
    details: str
    created_at: datetime


class SearchResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    document_id: int
    document_number: str
    title: str
    document_type: str
    classification: str
    current_version: int
    case_id: int
    case_number: str
    case_title: str
    filename: str | None = None
    sha256: str | None = None
    created_at: datetime
