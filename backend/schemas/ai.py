"""Safe public connection contracts. No OAuth credentials or callback parameters."""
from typing import Literal
from pydantic import Field
from backend.schemas.api import APIModel
from src.providers.contracts import ReasoningEffort


class EmptyRequest(APIModel):
    pass


class SignInRequest(APIModel):
    connection_id: str | None = Field(default=None, min_length=1, max_length=64)
    consent: bool = False


class ModelCheckRequest(APIModel):
    model: str = Field(min_length=1, max_length=255)


class ConnectionModel(APIModel):
    slug: str
    display_name: str
    supported_reasoning_levels: list[ReasoningEffort] = Field(default_factory=list)
    default_reasoning_level: ReasoningEffort | None = None


class CatalogResponse(APIModel):
    models: list[ConnectionModel]


class CheckResult(APIModel):
    model: str
    actual_model: str | None = None
    checked_at: float
    duration_seconds: float | None = None
    usage: dict[str, int | None] | None = None


class ProfileStatus(APIModel):
    id: str
    label: str
    state: Literal['connected', 'permission_required', 'reconnect_required']
    plan_enabled: bool
    identity_connected: bool
    catalog_checked: bool
    inference_checked: bool
    last_check: CheckResult | None = None
    welcome_pending: bool


class PendingStatus(APIModel):
    id: str
    state: Literal['waiting', 'exchanging']
    expires_at: float


class ConnectionStatus(APIModel):
    profiles: list[ProfileStatus]
    active_connection_id: str | None = None
    storage_mode: Literal['keyring', 'memory']
    error: str | None = None
    pending: PendingStatus | None = None


class SessionResponse(APIModel):
    csrf: str


class LaunchResponse(APIModel):
    launch_path: str


class LogoutResponse(APIModel):
    local_signed_out: bool
    remote_revocation_confirmed: bool
    keyring_cleanup_confirmed: bool
