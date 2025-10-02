import httpx
from typing import Dict, Any, List, Optional
from cron_services.config import cron_settings as settings
import logging
import json

logger = logging.getLogger(__name__)


class RenderAPIClient:
    def __init__(self):
        self.base_url = settings.render_api_base_url
        self.api_key = settings.render_api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _make_request(
        self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}{endpoint}"

            # Log the request payload for debugging
            if data:
                logger.info(f"Render API Request: {method} {url}")
                logger.debug(f"Request payload: {json.dumps(data, indent=2)}")

            response = await client.request(
                method=method, url=url, headers=self.headers, json=data
            )

            # Better error handling with response body
            if not response.is_success:
                error_body = response.text
                logger.error(f"Render API Error: {response.status_code} - {error_body}")
                try:
                    error_json = response.json()
                    logger.error(f"Error details: {json.dumps(error_json, indent=2)}")
                except:
                    pass
                response.raise_for_status()

            return response.json()

    async def create_cron_job(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new cron job service"""
        return await self._make_request("POST", "/services", service_data)

    async def trigger_cron_job(self, service_id: str) -> Dict[str, Any]:
        """Trigger a cron job run"""
        return await self._make_request("POST", f"/services/{service_id}/runs")

    async def cancel_cron_job_run(self, service_id: str, run_id: str) -> Dict[str, Any]:
        """Cancel a running cron job"""
        return await self._make_request("DELETE", f"/services/{service_id}/runs/{run_id}")

    async def list_services(self, service_type: str = "cron_job") -> List[Dict[str, Any]]:
        """List all services, optionally filtered by type"""
        params = f"?type={service_type}" if service_type else ""
        return await self._make_request("GET", f"/services{params}")

    async def get_service(self, service_id: str) -> Dict[str, Any]:
        """Get details of a specific service"""
        return await self._make_request("GET", f"/services/{service_id}")

    async def update_service(self, service_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a service (including cron schedule)"""
        return await self._make_request("PATCH", f"/services/{service_id}", update_data)

    async def delete_service(self, service_id: str) -> Dict[str, Any]:
        """Delete a service"""
        return await self._make_request("DELETE", f"/services/{service_id}")

    async def list_service_runs(self, service_id: str) -> List[Dict[str, Any]]:
        """List runs for a specific service"""
        return await self._make_request("GET", f"/services/{service_id}/runs")

