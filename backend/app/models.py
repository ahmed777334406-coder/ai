import enum
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator
from app.database import Base

try:
    from pgvector.sqlalchemy import Vector as PgVector
except Exception:  # pgvector is installed in the production requirements; SQLite tests use JSON.
    PgVector = None

class EmbeddingVector(TypeDecorator):
    impl = JSON
    cache_ok = True
    def __init__(self, dimensions: int):
        self.dimensions = dimensions
        super().__init__()
    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and PgVector is not None:
            return dialect.type_descriptor(PgVector(self.dimensions))
        return dialect.type_descriptor(JSON())
    def process_result_value(self, value, dialect):
        return [float(v) for v in value] if value is not None else None
    def process_bind_param(self, value, dialect):
        return [float(v) for v in value] if value is not None else None

class ListingStatus(str, enum.Enum):
    LOST = "LOST"
    FOUND = "FOUND"

class ListingState(str, enum.Enum):
    OPEN = "OPEN"
    CLAIM_PENDING = "CLAIM_PENDING"
    RECOVERED = "RECOVERED"
    CLOSED = "CLOSED"
    UNDER_REVIEW = "UNDER_REVIEW"

class ClaimStatus(str, enum.Enum):
    PENDING = "PENDING"
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class UserRole(str, enum.Enum):
    STUDENT = "STUDENT"
    ADMIN = "ADMIN"

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.STUDENT)
    preferred_language: Mapped[str] = mapped_column(String(5), default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    listings: Mapped[list["Listing"]] = relationship(back_populates="owner")

class CampusZone(Base):
    __tablename__ = "campus_zones"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name_en: Mapped[str] = mapped_column(String(100))
    name_zh: Mapped[str] = mapped_column(String(100))
    adjacent_codes: Mapped[list] = mapped_column(JSON, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Listing(Base):
    __tablename__ = "listings"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[ListingStatus] = mapped_column(Enum(ListingStatus), index=True)
    state: Mapped[ListingState] = mapped_column(Enum(ListingState), default=ListingState.OPEN, index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80), index=True)
    color: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("campus_zones.id"), nullable=True, index=True)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    client_request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    private_identifiers: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    owner: Mapped[User] = relationship(back_populates="listings")
    zone: Mapped[CampusZone | None] = relationship()
    images: Mapped[list["ListingImage"]] = relationship(back_populates="listing", cascade="all, delete-orphan")
    __table_args__ = (Index("ix_listing_status_state", "status", "state"), UniqueConstraint("owner_id", "client_request_id", name="uq_listing_owner_request"))

class ListingImage(Base):
    __tablename__ = "listing_images"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    storage_path: Mapped[str] = mapped_column(String(500))
    public_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    mime_type: Mapped[str] = mapped_column(String(80))
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    listing: Mapped[Listing] = relationship(back_populates="images")

class ListingAIAnalysis(Base):
    __tablename__ = "listing_ai_analysis"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(60))
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class TextEmbedding(Base):
    __tablename__ = "text_embeddings"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), unique=True, index=True)
    vector: Mapped[list | None] = mapped_column(EmbeddingVector(384), nullable=True)
    method: Mapped[str] = mapped_column(String(80))
    dimensions: Mapped[int] = mapped_column(Integer, default=384)
    __table_args__ = (Index("ix_text_embeddings_vector", "vector", postgresql_using="hnsw", postgresql_ops={"vector": "vector_cosine_ops"}),)

class ImageEmbedding(Base):
    __tablename__ = "image_embeddings"
    id: Mapped[int] = mapped_column(primary_key=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("listing_images.id", ondelete="CASCADE"), unique=True, index=True)
    vector: Mapped[list | None] = mapped_column(EmbeddingVector(512), nullable=True)
    method: Mapped[str] = mapped_column(String(100))
    dimensions: Mapped[int] = mapped_column(Integer, default=512)
    __table_args__ = (Index("ix_image_embeddings_vector", "vector", postgresql_using="hnsw", postgresql_ops={"vector": "vector_cosine_ops"}),)

class Match(Base):
    __tablename__ = "matches"
    id: Mapped[int] = mapped_column(primary_key=True)
    lost_listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    found_listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    score: Mapped[float] = mapped_column(Float)
    components: Mapped[dict] = mapped_column(JSON, default=dict)
    methods: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="SUGGESTED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint("lost_listing_id", "found_listing_id", name="uq_lost_found_match"),)

class Claim(Base):
    __tablename__ = "claims"
    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), index=True)
    claimant_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id"), nullable=True)
    verification_details: Mapped[str] = mapped_column(Text)
    evidence_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[ClaimStatus] = mapped_column(Enum(ClaimStatus), default=ClaimStatus.PENDING, index=True)
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    dedupe_key: Mapped[str | None] = mapped_column(String(180), unique=True, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    target_type: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str] = mapped_column(String(80))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class MatchFeedback(Base):
    __tablename__ = "match_feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    relevant: Mapped[bool] = mapped_column(Boolean)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint("match_id", "user_id", name="uq_match_feedback_user"),)

class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
