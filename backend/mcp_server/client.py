"""
Thin async HTTP client that wraps the Boses REST API.
Every request carries the X-API-Key header — authentication and workspace
isolation are enforced entirely by the backend.
"""
import asyncio
from typing import Any

import httpx

from mcp_server.config import BOSES_API_URL, BOSES_API_KEY
from mcp_server.context import get_api_key

_TIMEOUT = httpx.Timeout(120.0, connect=10.0)


def _headers() -> dict[str, str]:
    # Per-session key takes priority over the env fallback (local dev / internal use)
    key = get_api_key() or BOSES_API_KEY
    return {"X-API-Key": key, "Content-Type": "application/json"}


def _raise_actionable(r: httpx.Response) -> None:
    """Raise a descriptive RuntimeError instead of a raw HTTP status error."""
    if r.is_success:
        return
    if r.status_code == 401:
        raise RuntimeError(
            "Invalid or missing API key. Go to Boses Settings → API Keys and check your key."
        )
    if r.status_code == 403:
        raise RuntimeError(
            "Access denied. Your API key does not have permission to access this resource."
        )
    if r.status_code == 404:
        raise RuntimeError(
            f"Resource not found (404). The project, persona group, or simulation ID may be incorrect."
        )
    if r.status_code == 422:
        detail = r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text
        raise RuntimeError(f"Invalid request: {detail}")
    if r.status_code == 429:
        raise RuntimeError(
            "Rate limit reached. Wait a moment before trying again."
        )
    if r.status_code >= 500:
        raise RuntimeError(
            f"Boses server error ({r.status_code}). This is likely a temporary issue — try again shortly."
        )
    r.raise_for_status()


async def _get(path: str, params: dict | None = None) -> Any:
    async with httpx.AsyncClient(base_url=BOSES_API_URL, timeout=_TIMEOUT) as client:
        r = await client.get(path, headers=_headers(), params=params)
        _raise_actionable(r)
        return r.json()


async def _post(path: str, body: dict | None = None) -> Any:
    async with httpx.AsyncClient(base_url=BOSES_API_URL, timeout=_TIMEOUT) as client:
        r = await client.post(path, headers=_headers(), json=body or {})
        _raise_actionable(r)
        return r.json()


async def _delete(path: str) -> None:
    async with httpx.AsyncClient(base_url=BOSES_API_URL, timeout=_TIMEOUT) as client:
        r = await client.delete(path, headers=_headers())
        _raise_actionable(r)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

async def list_projects() -> list[dict]:
    return await _get("/api/v1/projects")


async def create_project(name: str, description: str = "") -> dict:
    payload: dict = {"name": name}
    if description:
        payload["description"] = description
    return await _post("/api/v1/projects", payload)


# ---------------------------------------------------------------------------
# Persona groups
# ---------------------------------------------------------------------------

async def list_persona_groups(project_id: str) -> list[dict]:
    return await _get(f"/api/v1/projects/{project_id}/persona-groups")


async def parse_persona_prompt(project_id: str, prompt: str) -> dict:
    """Use the backend's /parse-prompt endpoint to extract structured demographic fields."""
    return await _post(f"/api/v1/projects/{project_id}/persona-groups/parse-prompt", {"prompt": prompt})


async def create_persona_group(project_id: str, payload: dict) -> dict:
    return await _post(f"/api/v1/projects/{project_id}/persona-groups", payload)


async def generate_persona_group(project_id: str, group_id: str) -> dict:
    return await _post(f"/api/v1/projects/{project_id}/persona-groups/{group_id}/generate")


async def get_persona_group(project_id: str, group_id: str) -> dict:
    return await _get(f"/api/v1/projects/{project_id}/persona-groups/{group_id}")


async def poll_persona_group_until_ready(
    project_id: str,
    group_id: str,
    timeout_seconds: int = 180,
    interval_seconds: int = 5,
) -> dict:
    """Poll generation_status until 'complete' or 'failed', or timeout."""
    elapsed = 0
    while elapsed < timeout_seconds:
        group = await get_persona_group(project_id, group_id)
        status = group.get("generation_status")
        if status == "complete":
            return group
        if status == "failed":
            raise RuntimeError(f"Persona group generation failed: {group.get('generation_metadata')}")
        await asyncio.sleep(interval_seconds)
        elapsed += interval_seconds
    raise TimeoutError(f"Persona group generation did not complete within {timeout_seconds}s")


# ---------------------------------------------------------------------------
# Simulations
# ---------------------------------------------------------------------------

async def create_simulation(project_id: str, payload: dict) -> dict:
    return await _post(f"/api/v1/projects/{project_id}/simulations", payload)


async def get_simulation(project_id: str, simulation_id: str) -> dict:
    return await _get(f"/api/v1/projects/{project_id}/simulations/{simulation_id}")


async def get_simulation_results(project_id: str, simulation_id: str) -> list[dict]:
    return await _get(f"/api/v1/projects/{project_id}/simulations/{simulation_id}/results")
