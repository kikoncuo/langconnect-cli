import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

from .exceptions import LangConnectRequestError, MissingEnvironmentVariable

logger = logging.getLogger(__name__)


def _env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise MissingEnvironmentVariable(f"'{name}' environment variable not set!")
    return value


class LangConnectClient:
    """Async client to interact with the LangConnect API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        admin_email: Optional[str] = None,
        admin_password: Optional[str] = None,
        timeout: int = 90,
    ) -> None:
        base = base_url or _env("LANGCONNECT_BASE_URL")
        self.base_url = base[:-1] if base.endswith("/") else base
        self.api_key = _env("LANGCONNECT_API_KEY")
        if not self.api_key:
            self.admin_email = admin_email or _env("LANGCONNECT_ADMIN_EMAIL")
            self.admin_password = admin_password or _env("LANGCONNECT_ADMIN_PASSWORD")
        else:
            self.admin_email = None
            self.admin_password = None
        self.timeout = timeout
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.headers: Dict[str, str] = {}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"            

    async def signin(self) -> bool:
        """Authenticate using admin credentials."""
        if self.api_key:
            logger.info('Logging using API KEY...')
            return True
        
        if not self.admin_email or not self.admin_password:
             logger.error("Admin email or password not configured. Cannot sign in.")
             return False

        payload = {"email": self.admin_email, "password": self.admin_password}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(f"{self.base_url}/auth/signin", json=payload)
                response.raise_for_status()
            except httpx.RequestError as exc:
                logger.error(f"Request to signin endpoint failed: {exc}")
                return False

        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            await self._update_auth_header()
            return True

        logger.error("Failed to sign in: %s - %s", response.status_code, response.text)
        return False
    
    async def _ensure_authenticated(self) -> None:
        """
        Ensures that the client is authenticated before making a request.
        If not authenticated, it will attempt to sign in.
        """
        if "Authorization" in self.headers:
            return

        if not self.access_token:
            logger.info("No active session or API key. Trying to sign-in...")
            if not await self.signin():
                raise LangConnectRequestError("Authentication failed. Provide a valid API KEY or admin credentials in the .env file.")
    
    async def _update_auth_header(self) -> None:
        """
        Sets or clears the authorization header based on the current auth state.
        Priority: API KEY > Access Token
        """
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.access_token:
            self.headers["Authorization"] = f"Bearer {self.access_token}"
        else:
            # If no credentials are available, remove the header to invalidate the session.
            self.headers.pop("Authorization", None)

    async def refresh_access_token(self) -> bool:
        if not self.refresh_token:
            logger.error("No refresh token available to refresh access token.")
            return False

        # According to API spec, refresh_token should be passed as a query parameter
        params = {"refresh_token": self.refresh_token}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/auth/refresh", params=params)

        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")  # Update refresh token as well
            await self._update_auth_header()
            return True

        logger.error("Failed to refresh token: %s - %s", response.status_code, response.text)
        return False

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        await self._ensure_authenticated()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self._build_url(endpoint), headers=self.headers, params=params)
                response.raise_for_status()
                return response.json() if response.content else None
        except httpx.HTTPStatusError as exc:
            logger.error("GET %s failed: %s - %s", endpoint, exc.response.status_code, exc.response.text)
        except httpx.RequestError as exc:
            logger.error(f"Request failed for GET {endpoint}: {exc}")
        return None

    async def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        await self._ensure_authenticated()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self._build_url(endpoint),
                headers=self.headers,
                data=data,
                json=json_data,
                files=files,
            )

        if response.status_code in {200, 201}:
            try:
                return response.json() if response.content else None
            except json.JSONDecodeError:
                return {"message": response.text}

        logger.error("POST %s failed: %s - %s", endpoint, response.status_code, response.text)
        return None

    async def delete(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        await self._ensure_authenticated()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(self._build_url(endpoint), headers=self.headers, params=params)

        if response.status_code in {200, 204}:
            return response.json() if response.content else None

        logger.error("DELETE %s failed: %s - %s", endpoint, response.status_code, response.text)
        return {"error": response.text, "status": response.status_code}

    def _build_url(self, endpoint: str) -> str:
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]
        return f"{self.base_url}/{endpoint}" if endpoint else self.base_url

    # Additional convenience methods for common API endpoints
    
    async def signup(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Sign up a new user."""
        payload = {"email": email, "password": password}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/auth/signup", json=payload)

        if response.status_code == 200:
            data = response.json()
            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            await self._update_auth_header()
            return data

        logger.error("Failed to sign up: %s - %s", response.status_code, response.text)
        return None

    async def signout(self) -> bool:
        """Sign out the current user."""
        await self._ensure_authenticated()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/auth/signout", headers=self.headers)

        if response.status_code == 200:
            self.access_token = None
            self.refresh_token = None
            await self._update_auth_header()
            return True

        logger.error("Failed to sign out: %s - %s", response.status_code, response.text)
        return False

    async def get_current_user(self) -> Optional[Dict[str, Any]]:
        """Get current authenticated user information."""
        return await self.get("auth/me")

    async def list_collections(self) -> Optional[List[Dict[str, Any]]]:
        """List all collections."""
        return await self.get("collections")

    async def create_collection(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Create a new collection."""
        payload = {"name": name}
        if metadata:
            payload["metadata"] = metadata
        return await self.post("collections", json_data=payload)

    async def get_collection(self, collection_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific collection."""
        result = await self.get(f"collections/{collection_id}")
        
        # Workaround for API bug: individual collection endpoint doesn't show updated counts
        # Get accurate counts from list-collections endpoint
        if result:
            collections_list = await self.get("collections")
            if collections_list:
                for collection in collections_list:
                    if collection.get("uuid") == collection_id:
                        result["document_count"] = collection.get("document_count", 0)
                        result["chunk_count"] = collection.get("chunk_count", 0)
                        break
        
        return result

    async def update_collection(self, collection_id: str, name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Update a collection."""
        payload = {}
        if name:
            payload["name"] = name
        if metadata:
            payload["metadata"] = metadata
        
        await self._ensure_authenticated()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.patch(
                f"{self.base_url}/collections/{collection_id}",
                headers=self.headers,
                json=payload
            )

        if response.status_code == 200:
            return response.json() if response.content else None

        logger.error("PATCH collections/%s failed: %s - %s", collection_id, response.status_code, response.text)
        return None

    async def delete_collection(self, collection_id: str) -> bool:
        """Delete a collection."""
        await self._ensure_authenticated()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(f"{self.base_url}/collections/{collection_id}", headers=self.headers)

        if response.status_code == 204:
            return True

        logger.error("DELETE collections/%s failed: %s - %s", collection_id, response.status_code, response.text)
        return False

    async def list_documents(self, collection_id: str, limit: int = 10, offset: int = 0) -> Optional[List[Dict[str, Any]]]:
        """List documents in a collection."""
        params = {"limit": limit, "offset": offset}
        return await self.get(f"collections/{collection_id}/documents", params)

    async def upload_documents(self, collection_id: str, files: List[str], metadatas_json: Optional[str] = None, chunk_size: int = 1000, chunk_overlap: int = 200) -> Optional[Dict[str, Any]]:
        """Upload documents to a collection."""
        await self._ensure_authenticated()
        
        files_data = []
        for file_path in files:
            with open(file_path, 'rb') as f:
                files_data.append(('files', (file_path, f.read())))

        form_data = {
            'chunk_size': chunk_size,
            'chunk_overlap': chunk_overlap
        }
        if metadatas_json:
            form_data['metadatas_json'] = metadatas_json

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/collections/{collection_id}/documents",
                headers=self.headers,
                data=form_data,
                files=files_data
            )

        if response.status_code == 200:
            return response.json() if response.content else None

        logger.error("POST documents failed: %s - %s", response.status_code, response.text)
        return None

    async def search_documents(
        self, 
        collection_id: str, 
        query: str, 
        limit: int = 10, 
        search_type: str = "semantic", 
        filter_dict: Optional[Dict[str, Any]] = None,
        language: str = "es"
    ) -> Optional[List[Dict[str, Any]]]:
        """Search documents in a collection."""
        payload = {
            "query": query,
            "limit": limit,
            "search_type": search_type,
            "language": language
        }
        if filter_dict:
            payload["filter"] = filter_dict
        
        return await self.post(f"collections/{collection_id}/documents/search", json_data=payload)

    async def delete_document(self, collection_id: str, document_id: str, delete_by: str = "document_id") -> Optional[Dict[str, Any]]:
        """Delete a document from a collection."""
        params = {"delete_by": delete_by}
        return await self.delete(f"collections/{collection_id}/documents/{document_id}", params)

    async def bulk_delete_documents(self, collection_id: str, document_ids: Optional[List[str]] = None, file_ids: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Bulk delete documents from a collection."""
        payload = {}
        if document_ids:
            payload["document_ids"] = document_ids
        if file_ids:
            payload["file_ids"] = file_ids
        
        await self._ensure_authenticated()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(
                f"{self.base_url}/collections/{collection_id}/documents",
                headers=self.headers,
                json=payload
            )

        if response.status_code == 200:
            return response.json() if response.content else None

        logger.error("DELETE documents failed: %s - %s", response.status_code, response.text)
        return None

    async def health_check(self) -> Optional[Dict[str, Any]]:
        """Check API health."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/health")

        if response.status_code == 200:
            return response.json() if response.content else None

        logger.error("Health check failed: %s - %s", response.status_code, response.text)
        return None
