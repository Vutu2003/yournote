"""Marker integrity only; evaluate semantic support separately."""
import re
from src.errors import LLMServiceError, LLMErrorCode


def validate_markers(text,valid):
    if not set(re.findall(r'\[(S[1-9][0-9]*)\]',text)) <= valid:
        raise LLMServiceError.for_code(LLMErrorCode.INVALID_RESPONSE)
