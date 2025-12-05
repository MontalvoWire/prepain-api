import os
from typing import Any, Dict

import httpx
from fastapi import HTTPException

MOODLE_BASE_URL = "https://prepa.in/webservice/rest/server.php"
MOODLE_STUDENT_ROLE_ID = 5

_token_env_value = os.getenv("MOODLE_TOKEN")
print("MOODLE_TOKEN presente:", bool(_token_env_value), "prefijo:", (_token_env_value or "")[:4])


def _get_moodle_token() -> str:
    token = os.getenv("MOODLE_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="Configuración inválida: falta MOODLE_TOKEN")
    return token



async def call_moodle(function_name: str, params: Dict[str, Any]) -> Any:
    token = _get_moodle_token()
    payload: Dict[str, Any] = {
        "wstoken": token,
        "wsfunction": function_name,
        "moodlewsrestformat": "json",
    }
    payload.update(params)

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(MOODLE_BASE_URL, data=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502, detail=f"Moodle devolvió un error HTTP {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="No se pudo conectar con Moodle") from exc

    data = response.json()
    if isinstance(data, dict) and data.get("exception"):
        message = data.get("message") or "Error en la respuesta de Moodle"
        raise HTTPException(status_code=400, detail=message)

    return data
