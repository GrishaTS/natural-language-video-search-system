import asyncio
import time
from typing import Any

import httpx
from loguru import logger
from src.core.config import settings


class VmsClient:
    """Async HTTP client for the VMS API.

    Handles Bearer token auth (static or OAuth2 with auto-refresh), retry logic with exponential backoff, and JSON/binary/multipart requests.
    """

    def __init__(self) -> None:
        self.api_url = settings.VMS_API_URL.rstrip("/")
        self.bearer_token = settings.VMS_BEARER_TOKEN
        self.username = settings.VMS_USERNAME
        self.password = settings.VMS_PASSWORD
        self.frontend_url = settings.VMS_FRONTEND_URL.rstrip("/")
        self._token: str | None = None
        self._token_expires_at: float | None = None
        self._lock = asyncio.Lock()
        self._client = httpx.AsyncClient(
            base_url=self.api_url,
            timeout=httpx.Timeout(15.0, connect=5.0),
        )

    def _token_valid(self) -> bool:
        """Return True if the cached token exists and has not expired."""

        return (
            bool(self._token)
            and self._token_expires_at is not None
            and self._token_expires_at > time.monotonic()
        )

    async def _get_token(self) -> str:
        """Return a valid Bearer token, refreshing via OAuth2 if needed.

        Uses a double-checked lock to avoid concurrent refresh races. Falls back to ``VMS_BEARER_TOKEN`` if configured; otherwise authenticates with username/password credentials.

        Raises:
            ValueError: If neither a static token nor credentials are configured, or if the auth response contains no token.
        """

        if self.bearer_token:
            return self.bearer_token

        if self._token_valid():
            return self._token or ""

        async with self._lock:
            if self._token_valid():
                return self._token or ""

            if not (self.username and self.password):
                raise ValueError("No valid authentication token available")

            oauth_endpoint = f"{self.api_url}/oauth2/oauth2/v1/auth/authenticate"
            response = await self._client.post(
                oauth_endpoint,
                json={
                    "name": self.username,
                    "password": self.password,
                    "one_time_password": "",
                    "rememberme": True,
                },
                headers={
                    "Content-Type": "application/json",
                    "accept": "*/*",
                },
            )
            response.raise_for_status()
            data = response.json()
            token = data.get("token") or data.get("access_token")

            if not token:
                raise ValueError("No access token in response")

            ttl_seconds = int(data.get("expires_in") or data.get("expires") or 3600)
            ttl_seconds = max(ttl_seconds, 60)
            self._token_expires_at = time.monotonic() + ttl_seconds
            self._token = token
            return token

    async def request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        request_id: str | None = None,
        retries: int = 3,
    ) -> Any:
        """Send an authenticated JSON request to the VMS API.

        Args:
            method: HTTP method, for example ``"GET"`` or ``"POST"``.
            endpoint: Path or full URL; relative paths are prepended with the base URL.
            json_data: Request body serialized as JSON.
            params: URL query parameters.
            request_id: Optional correlation ID sent as the ``X-Request-ID`` header.
            retries: Number of attempts before raising.

        Returns:
            Parsed JSON response as a Python object.

        Raises:
            httpx.HTTPStatusError: On non-2xx response after all retries.
            httpx.TimeoutException: If all attempts time out.
            RuntimeError: If all retries are exhausted without a successful response.
        """

        token = await self._get_token()
        url = endpoint if endpoint.startswith("http") else f"{self.api_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        if request_id:
            headers["X-Request-ID"] = request_id

        for attempt in range(retries):
            try:
                started = time.monotonic()
                response = await self._client.request(
                    method, url, headers=headers, json=json_data, params=params
                )

                if response.status_code != 200:
                    logger.warning(
                        f"VMS API {request_id}: {response.status_code}: {response.text}"
                    )

                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException:
                logger.warning(
                    f"VMS request timeout on attempt {attempt + 1}/{retries}"
                )

                if attempt == retries - 1:
                    raise

                await asyncio.sleep(2**attempt)

            except httpx.HTTPStatusError as exc:
                resp = exc.response
                body_text = ""

                if resp is not None:
                    try:
                        body_text = resp.text

                        if not body_text and resp.content:
                            body_text = resp.content.decode(errors="ignore")

                    except Exception:
                        body_text = "<failed to decode body>"

                logger.error(
                    f"VMS API error {resp.status_code if resp else 'unknown'} "
                    f"{getattr(resp, 'reason_phrase', '') or ''}: {body_text or '<empty body>'}"
                )

                if json_data:
                    logger.error(f"Request body: {json_data}")

                raise

            except Exception as exc:
                logger.error(f"VMS API request failed: {exc}")

                if attempt == retries - 1:
                    raise

                await asyncio.sleep(2**attempt)

        raise RuntimeError("Failed after retries")

    async def request_multipart(
        self,
        method: str,
        endpoint: str,
        file_bytes: bytes,
        file_field: str = "file",
        file_name: str = "image.png",
        content_type: str = "image/png",
        retries: int = 3,
    ) -> Any:
        """Send a multipart/form-data request and return parsed JSON.

        Args:
            method: HTTP method.
            endpoint: Path or full URL.
            file_bytes: Raw file content to upload.
            file_field: Form field name for the file part.
            file_name: Filename sent in the Content-Disposition header.
            content_type: MIME type of the file.
            retries: Number of attempts before raising.

        Returns:
            Parsed JSON response.

        Raises:
            httpx.HTTPStatusError: On non-2xx response after all retries.
            httpx.TimeoutException: If all attempts time out.
            RuntimeError: If all retries are exhausted.
        """

        token = await self._get_token()
        url = endpoint if endpoint.startswith("http") else f"{self.api_url}{endpoint}"
        headers = {"Authorization": f"Bearer {token}"}

        for attempt in range(retries):
            try:
                response = await self._client.request(
                    method,
                    url,
                    headers=headers,
                    files={file_field: (file_name, file_bytes, content_type)},
                )
                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException:
                logger.warning(
                    f"VMS multipart timeout on attempt {attempt + 1}/{retries}"
                )

                if attempt == retries - 1:
                    raise

                await asyncio.sleep(2**attempt)

            except httpx.HTTPStatusError as exc:
                resp = exc.response
                body_text = resp.text if resp else "<empty>"
                logger.error(f"VMS multipart error {resp.status_code}: {body_text}")
                raise

            except Exception as exc:
                logger.error(f"VMS multipart request failed: {exc}")

                if attempt == retries - 1:
                    raise

                await asyncio.sleep(2**attempt)

        raise RuntimeError("Failed after retries (multipart)")

    async def request_binary(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        request_id: str | None = None,
        retries: int = 3,
    ) -> tuple[bytes, str | None]:
        """Send an authenticated request and return raw bytes with content type.

        Args:
            method: HTTP method.
            endpoint: Path or full URL.
            params: URL query parameters.
            request_id: Optional correlation ID sent as the ``X-Request-ID`` header.
            retries: Number of attempts before raising.

        Returns:
            Tuple of raw response body and content-type header value or None.

        Raises:
            httpx.HTTPStatusError: On non-2xx response after all retries.
            httpx.TimeoutException: If all attempts time out.
            RuntimeError: If all retries are exhausted.
        """

        token = await self._get_token()
        url = endpoint if endpoint.startswith("http") else f"{self.api_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
        }

        if request_id:
            headers["X-Request-ID"] = request_id

        for attempt in range(retries):
            try:
                response = await self._client.request(
                    method, url, headers=headers, params=params
                )
                response.raise_for_status()
                return response.content, response.headers.get("content-type")

            except httpx.TimeoutException:
                logger.warning(
                    f"VMS binary request timeout on attempt {attempt + 1}/{retries}"
                )

                if attempt == retries - 1:
                    raise

                await asyncio.sleep(2**attempt)

            except httpx.HTTPStatusError as exc:
                resp = exc.response
                body_text = ""

                if resp is not None:
                    try:
                        body_text = resp.text

                    except Exception:
                        body_text = "<failed to decode body>"

                logger.error(
                    f"VMS binary API error {resp.status_code if resp else 'unknown'} "
                    f"{getattr(resp, 'reason_phrase', '') or ''}: {body_text or '<empty body>'}"
                )

                if attempt == retries - 1:
                    raise

                await asyncio.sleep(2**attempt)

            except Exception as exc:
                logger.error(f"VMS binary request failed: {exc}")

                if attempt == retries - 1:
                    raise

                await asyncio.sleep(2**attempt)

        raise RuntimeError("Failed after retries (binary)")

    async def aclose(self) -> None:
        """Close the underlying httpx client."""

        await self._client.aclose()


_vms_client: VmsClient | None = None


def get_vms_client() -> VmsClient:
    """Return the shared singleton VmsClient, creating it on first call."""

    global _vms_client

    if _vms_client is None:
        _vms_client = VmsClient()
        logger.info(f"VMS client created for {settings.VMS_API_URL}")

    return _vms_client


async def aclose_vms_client() -> None:
    """Close and discard the shared VmsClient singleton."""

    global _vms_client
    client = _vms_client

    if client is None:
        return

    try:
        await client.aclose()
        logger.info("VMS client closed")

    finally:
        _vms_client = None


def _shorten(data: Any, limit: int = 1000) -> str:
    """Safely convert payload to a string and truncate for log output."""

    try:
        text = str(data)

    except Exception:
        return "<unserializable payload>"

    if len(text) > limit:
        return text[:limit] + "...(truncated)"

    return text
