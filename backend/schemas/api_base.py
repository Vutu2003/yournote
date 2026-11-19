"""Shared public model base; avoid generation/response import cycles."""
from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    model_config = ConfigDict(extra='forbid')
