from typing import Dict, Any, List
from cron_services.render_client import RenderAPIClient
from cron_models.cron_job import CronJobCreate, CronJobUpdate, EnvironmentVar


class CronJobService:
    def __init__(self):
        self.render_client = RenderAPIClient()

    def _build_environment_vars(self, cron_job_data: CronJobCreate) -> List[Dict[str, str]]:
        """Build environment variables for the cron job"""
        env_vars = [
            {"key": "CUSTOMER_USERNAME", "value": cron_job_data.username},
            {"key": "CUSTOMER_PASSWORD", "value": cron_job_data.password},
            {"key": "CUSTOMER_PHONE", "value": cron_job_data.phone_number},
        ]

        # Add any additional environment variables
        if cron_job_data.additional_env_vars:
            for env_var in cron_job_data.additional_env_vars:
                env_vars.append({"key": env_var.key, "value": env_var.value})

        return env_vars

    def _build_service_payload(self, cron_job_data: CronJobCreate) -> Dict[str, Any]:
        """Build the service payload for Render API"""
        env_vars = self._build_environment_vars(cron_job_data)

        payload = {
            "type": "cron",
            "name": cron_job_data.name,
            "ownerID": "tea-cva20nd2ng1s73ff6a1g",
            "repo": cron_job_data.repo_url,
            "branch": cron_job_data.branch,
            "schedule": cron_job_data.schedule,
            "startCommand": cron_job_data.start_command,
            "envVars": env_vars,
            "runtime": "docker"
        }

        return payload

    async def create_cron_job(self, cron_job_data: CronJobCreate) -> Dict[str, Any]:
        """Create a new cron job"""
        payload = self._build_service_payload(cron_job_data)
        result = await self.render_client.create_cron_job(payload)
        return result

    async def trigger_cron_job(self, service_id: str) -> Dict[str, Any]:
        """Trigger a cron job manually"""
        return await self.render_client.trigger_cron_job(service_id)

    async def cancel_cron_job_run(self, service_id: str, run_id: str) -> Dict[str, Any]:
        """Cancel a running cron job"""
        return await self.render_client.cancel_cron_job_run(service_id, run_id)

    async def list_cron_jobs(self) -> List[Dict[str, Any]]:
        """List all cron jobs"""
        return await self.render_client.list_services("cron")

    async def get_cron_job(self, service_id: str) -> Dict[str, Any]:
        """Get details of a specific cron job"""
        return await self.render_client.get_service(service_id)

    async def update_cron_job(self, service_id: str, update_data: CronJobUpdate) -> Dict[str, Any]:
        """Update a cron job"""
        payload = {}

        if update_data.name:
            payload["name"] = update_data.name
        if update_data.schedule:
            payload["schedule"] = update_data.schedule

        # Handle environment variable updates
        if any([update_data.username, update_data.password, update_data.phone_number, update_data.additional_env_vars]):
            # Get current service to preserve existing env vars
            current_service = await self.render_client.get_service(service_id)
            current_env_vars = current_service.get("envVars", [])

            # Update the specific customer variables
            env_vars_dict = {env["key"]: env["value"] for env in current_env_vars}

            if update_data.username:
                env_vars_dict["CUSTOMER_USERNAME"] = update_data.username
            if update_data.password:
                env_vars_dict["CUSTOMER_PASSWORD"] = update_data.password
            if update_data.phone_number:
                env_vars_dict["CUSTOMER_PHONE"] = update_data.phone_number

            # Add additional env vars if provided
            if update_data.additional_env_vars:
                for env_var in update_data.additional_env_vars:
                    env_vars_dict[env_var.key] = env_var.value

            payload["envVars"] = [{"key": k, "value": v} for k, v in env_vars_dict.items()]

        return await self.render_client.update_service(service_id, payload)

    async def delete_cron_job(self, service_id: str) -> Dict[str, Any]:
        """Delete a cron job"""
        return await self.render_client.delete_service(service_id)

    async def list_cron_job_runs(self, service_id: str) -> List[Dict[str, Any]]:
        """List runs for a specific cron job"""
        return await self.render_client.list_service_runs(service_id)

