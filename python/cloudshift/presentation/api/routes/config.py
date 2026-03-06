"""Config routes -- GET /api/config, PUT /api/config."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from cloudshift.presentation.api.dependencies import get_container
from cloudshift.presentation.api.schemas import ConfigResponse, ConfigUpdateBody

router = APIRouter(prefix="/api/config", tags=["config"])

# In-memory mutable config; in production this would be backed by persistence.
_config: dict[str, Any] = {
    "source_provider": None,
    "target_provider": None,
    "default_strategy": "conservative",
    "max_parallel": 4,
    "backup_enabled": True,
    "extra": {},
}


@router.get(
    "",
    response_model=ConfigResponse,
    summary="Get current configuration",
)
async def get_config(
    container: Any = Depends(get_container),
) -> ConfigResponse:
    return ConfigResponse(**_config)


@router.put(
    "",
    response_model=ConfigResponse,
    summary="Update configuration",
)
async def update_config(
    body: ConfigUpdateBody,
    container: Any = Depends(get_container),
) -> ConfigResponse:
    updates = body.model_dump(exclude_none=True)
    for key, value in updates.items():
        if key == "extra" and isinstance(value, dict):
            _config.setdefault("extra", {}).update(value)
        else:
            _config[key] = value
    return ConfigResponse(**_config)
