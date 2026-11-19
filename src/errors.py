"""Provider-independent failures. Public HTTP responses still expose only detail."""

from enum import StrEnum


class LLMErrorCode(StrEnum):
    UNKNOWN = "unknown"
    NOT_CONFIGURED = "not_configured"
    RECONNECT_REQUIRED = "reconnect_required"
    MODEL_UNAVAILABLE = "model_unavailable"
    QUOTA_EXCEEDED = "quota_exceeded"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    INVALID_RESPONSE = "invalid_response"
    INVALID_REQUEST = "invalid_request"
    UNSUPPORTED_PROVIDER = "unsupported_provider"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    REQUEST_REJECTED = "request_rejected"
    CANCELLED = "cancelled"
    NOT_ELIGIBLE = "not_eligible"
    PERMISSION_REQUIRED = "permission_required"


_FAILURES = {
    LLMErrorCode.UNKNOWN: (502, "AI service rejected the request."),
    LLMErrorCode.NOT_CONFIGURED: (503, "AI service is not configured."),
    LLMErrorCode.RECONNECT_REQUIRED: (502, "AI service authentication failed."),
    LLMErrorCode.MODEL_UNAVAILABLE: (502, "Configured AI model is unavailable."),
    LLMErrorCode.QUOTA_EXCEEDED: (429, "AI service quota exceeded."),
    LLMErrorCode.RATE_LIMITED: (429, "AI service rate limit exceeded."),
    LLMErrorCode.TIMEOUT: (504, "AI service timed out."),
    LLMErrorCode.TEMPORARILY_UNAVAILABLE: (503, "AI service is temporarily unavailable."),
    LLMErrorCode.INVALID_RESPONSE: (502, "AI service returned an empty response."),
    LLMErrorCode.INVALID_REQUEST: (422, "Invalid AI request."),
    LLMErrorCode.UNSUPPORTED_PROVIDER: (503, "Configured AI provider is unavailable."),
    LLMErrorCode.UNSUPPORTED_CAPABILITY: (422, "AI service does not support this operation."),
    LLMErrorCode.REQUEST_REJECTED: (502, "AI service rejected the request."),
    LLMErrorCode.CANCELLED: (499, "AI request was cancelled."),
    LLMErrorCode.NOT_ELIGIBLE: (403, "ChatGPT plan usage is unavailable for this account."),
    LLMErrorCode.PERMISSION_REQUIRED: (403, "ChatGPT plan permission is required."),
}


class LLMServiceError(RuntimeError):
    def __init__(self, status_code: int, detail: str, *, code: LLMErrorCode = LLMErrorCode.UNKNOWN):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.code = code

    @classmethod
    def for_code(cls, code: LLMErrorCode) -> "LLMServiceError":
        status, detail = _FAILURES[code]
        return cls(status, detail, code=code)
