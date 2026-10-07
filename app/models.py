from typing import Literal

from pydantic import BaseModel, Field


class Configuration(BaseModel):
    """Runtime capture configuration exposed by the REST API."""

    sample_rate_hz: int = Field(default=1_000_000, ge=1)
    channel_count: int = Field(default=16, ge=1, le=16)
    channels: list[int] = Field(default_factory=list)


class ConfigurationUpdate(BaseModel):
    """Partial configuration update accepted by the API."""

    sample_rate_hz: int | None = Field(default=None, ge=1)
    channel_count: int | None = Field(default=None, ge=1, le=16)
    channels: list[int] | None = None


class HardwareStatus(BaseModel):
    connected: bool
    device: str | None = None
    reason: str


class AcquisitionStatus(BaseModel):
    status: Literal["idle", "running", "stopped"]
    sample_count: int = 0


class CaptureRequest(BaseModel):
    data_time: float = Field(ge=0)
    channels: list[int] = Field(default_factory=list)
    sample_rate_hz: int = Field(default=50_000, ge=1)
    format: Literal["csv", "binary"] = "csv"


class CaptureResponse(BaseModel):
    capture_id: str
    status: Literal["completed", "failed"]
