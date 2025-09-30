from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr, validator

# --- Submission Model (Raw data expected from the client) ---

class SurveySubmission(BaseModel):
    """
    Schema for the incoming survey payload, used for initial validation.
    Includes all raw PII data (email, age).
    """
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr  # PII field (will be hashed)
    age: int = Field(..., ge=13, le=120)  # PII field (will be hashed)
    consent: bool = Field(..., description="Must be true to accept")
    rating: int = Field(..., ge=1, le=5)
    comments: Optional[str] = Field(None, max_length=1000)
    
    # Exercise 1: Optional user_agent field
    user_agent: Optional[str] = Field(None, description="The client's browser/OS identifier.")
    
    # Exercise 3: Optional submission_id field
    submission_id: Optional[str] = Field(None, description="Unique identifier provided by client.")


    @validator("comments")
    def _strip_comments(cls, v):
        # Existing validator: strips whitespace from comments
        return v.strip() if isinstance(v, str) else v

    @validator("consent")
    def _must_consent(cls, v):
        # Existing validator: ensures consent is true
        if v is not True:
            raise ValueError("consent must be true")
        return v
        
# --- Storage Model (Data stored on the server AFTER transformation) ---

class StoredSurveyRecord(BaseModel):
    """
    Schema for the data stored on the server.
    PII (email and age) is replaced with SHA-256 hashes.
    """
    name: str
    consent: bool
    rating: int
    comments: Optional[str]
    
    # Exercise 2: PII Protection - Storing only SHA-256 hashes
    email_hash: str = Field(..., description="SHA-256 hash of the original email address.")
    age_hash: str = Field(..., description="SHA-256 hash of the original age.")
    
    # Exercise 1 & 3 fields
    user_agent: Optional[str]
    submission_id: str = Field(..., description="Unique ID for the record (generated if not provided).")
    
    # Server Metadata (always required)
    received_at: datetime
    ip: str