from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

from .services import request_forwarding

ollama_router = APIRouter(tags=["ollama"])


@ollama_router.post(
    "/api/{proxy_path:path}",
    description="Forward request to best ollama endpoint for the model",
    response_description="Json response from the best ollama endpoint for the model",
)
@ollama_router.get(
    "/api/{proxy_path:path}",
    description="Forward request to best ollama endpoint for the model",
    response_description="Json response from the best ollama endpoint for the model",
)
@ollama_router.post(
    "/v1/{proxy_path:path}",
    description="Forward request to best ollama endpoint for the model",
    response_description="Json response from the best ollama endpoint for the model",
)
@ollama_router.get(
    "/v1/{proxy_path:path}",
    description="Forward request to best ollama endpoint for the model",
    response_description="Json response from the best ollama endpoint for the model",
)
async def _request_forwarding(
    response: StreamingResponse | PlainTextResponse | JSONResponse = Depends(request_forwarding),
):
    return response
