from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from app.models import CommandResponse
from app.services import dispatcher, parser, permission_service, repository


class CommandRequest(BaseModel):
    text: str
    confirmed: bool = False


def command_response_to_dict(response: CommandResponse) -> dict[str, Any]:
    return {
        "intent": {
            "intent": response.intent.intent,
            "params": response.intent.params,
            "requires_confirmation": response.intent.requires_confirmation,
            "raw_text": response.intent.raw_text,
        },
        "permission": {
            "requires_confirmation": response.permission.requires_confirmation,
            "reason": response.permission.reason,
        },
        "result": None
        if response.result is None
        else {
            "success": response.result.success,
            "message": response.result.message,
            "data": response.result.data,
        },
    }


def create_app() -> FastAPI:
    app = FastAPI(title="Amadda Local API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/snapshots/latest")
    def latest_snapshot() -> dict[str, Any]:
        record = repository.get_latest_snapshot()
        if record is None:
            return {"snapshot": None}
        return {
            "snapshot": {
                "snapshot_id": record.snapshot_id,
                "created_at": record.created_at.isoformat(),
                "items": [
                    {
                        "app_name": item.app_name,
                        "title": item.title,
                        "url": item.url,
                        "item_type": item.item_type,
                        "process_name": item.process_name,
                        "executable_path": item.executable_path,
                        "created_at": item.created_at.isoformat() if item.created_at else None,
                    }
                    for item in record.items
                ],
            }
        }

    @app.post("/command")
    def handle_command(request: CommandRequest) -> dict[str, Any]:
        intent = parser.parse(request.text)
        permission = permission_service.evaluate(intent)
        result = None
        if not permission.requires_confirmation or request.confirmed:
            result = dispatcher.dispatch(intent)
        response = CommandResponse(intent=intent, permission=permission, result=result)
        return command_response_to_dict(response)

    return app
