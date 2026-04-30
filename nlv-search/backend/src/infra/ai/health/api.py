from src.infra.ai.client import get_ai_client
from src.infra.ai.health.schemas import AIHealthResponse, AIHealthServicesResponse


class AIHealthAPI:
    """Client for AI service health-check endpoints."""

    async def health(self) -> AIHealthResponse:
        """Check if the AI service itself is healthy.

        Returns:
            AIHealthResponse with the overall status.
        """

        client = get_ai_client()
        response = await client.get("/health")
        response.raise_for_status()
        data = response.json()
        return AIHealthResponse.model_validate(data)

    async def health_services(self) -> AIHealthServicesResponse:
        """Check health of all upstream AI service dependencies.

        Returns:
            AIHealthServicesResponse with per-service statuses.
        """

        client = get_ai_client()
        response = await client.get("/health/services")
        response.raise_for_status()
        data = response.json()
        return AIHealthServicesResponse.model_validate(data)
