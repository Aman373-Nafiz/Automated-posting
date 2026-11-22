"""Pydantic models describing the API request and response."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.validators import extract_single_link, validate_message


class PostingRequest(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "message": "Check out our latest business platform and grow "
                "your online visibility. https://example.com"
            }
        },
    )

    message: str = Field(
        ...,
        description="Max 200 characters and exactly one http(s) CTA link.",
    )

    @field_validator("message")
    @classmethod
    def _check_message(cls, value: str) -> str:
        return validate_message(value)

    @property
    def cta_link(self) -> str:
        """The single, already-validated CTA link inside the message."""
        return extract_single_link(self.message)


class PlatformResult(BaseModel):
    platform: str
    status: Literal["success", "failed"]
    posted_url: str | None = None
    public_access: bool = False
    date: str | None = None
    time: str | None = None
    error: str | None = None


class PostingResponse(BaseModel):
    success: bool = Field(
        description="True when at least one platform accepted the post."
    )
    results: list[PlatformResult]