from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator, field_validator
from typing import Literal
from app.models import ListingStatus, ListingState, ClaimStatus, UserRole

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=10, max_length=128)
    preferred_language: Literal["en", "zh"] = "en"

class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    full_name: str
    role: UserRole
    preferred_language: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class ListingCreate(BaseModel):
    client_request_id: str | None = Field(default=None, min_length=16, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    @field_validator("title", "description", "category", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    status: ListingStatus
    title: str = Field(min_length=2, max_length=180)
    description: str = Field(min_length=5, max_length=5000)
    category: str = Field(min_length=2, max_length=80)
    color: str | None = Field(default=None, max_length=60)
    zone_id: int | None = None
    occurred_at: datetime | None = None
    private_identifiers: str | None = Field(default=None, max_length=3000)

class ListingUpdate(BaseModel):
    @field_validator("title", "description", "category", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    title: str | None = Field(default=None, min_length=2, max_length=180)
    description: str | None = Field(default=None, min_length=5, max_length=5000)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    color: str | None = Field(default=None, max_length=60)
    zone_id: int | None = None
    occurred_at: datetime | None = None
    state: ListingState | None = None

    @model_validator(mode="after")
    def validate_required_fields(self):
        for key in self.model_fields_set & {"title", "description", "category", "state"}:
            value = getattr(self, key)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"{key} cannot be empty")
        return self

class ListingOut(BaseModel):
    id: int
    owner_id: int
    owner_name: str
    status: ListingStatus
    state: ListingState
    title: str
    description: str
    category: str
    color: str | None
    zone_id: int | None
    zone_name_en: str | None
    zone_name_zh: str | None
    occurred_at: datetime | None
    image_urls: list[str]
    is_synthetic: bool
    created_at: datetime

class ClaimCreate(BaseModel):
    listing_id: int
    match_id: int | None = None
    verification_details: str = Field(min_length=10, max_length=3000)

class ClaimReview(BaseModel):
    status: ClaimStatus
    admin_note: str | None = None

class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=1000)
    status: ListingStatus | None = None
    limit: int = Field(default=10, ge=1, le=30)

class DescriptionRequest(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    description: str = Field(min_length=5, max_length=5000)
    language: str = "en"
    target_language: str | None = None

class FeedbackCreate(BaseModel):
    relevant: bool
    note: str | None = None


class DuplicateCheckRequest(BaseModel):
    status: ListingStatus
    title: str = Field(min_length=2, max_length=180)
    description: str = Field(min_length=5, max_length=5000)
    category: str = Field(min_length=2, max_length=80)
    color: str | None = Field(default=None, max_length=60)


class CampusZoneCreate(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    name_en: str = Field(min_length=2, max_length=100)
    name_zh: str = Field(min_length=2, max_length=100)
    adjacent_codes: list[str] = Field(default_factory=list)
    is_active: bool = True

class CampusZoneUpdate(BaseModel):
    name_en: str | None = Field(default=None, min_length=2, max_length=100)
    name_zh: str | None = Field(default=None, min_length=2, max_length=100)
    adjacent_codes: list[str] | None = None
    is_active: bool | None = None

class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    preferred_language: Literal["en", "zh"] | None = None

    @model_validator(mode="after")
    def reject_explicit_null(self):
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("Profile fields cannot be null")
        if self.full_name is not None:
            self.full_name = self.full_name.strip()
            if len(self.full_name) < 2:
                raise ValueError("Full name must contain at least two characters")
        return self
