from typing import Dict, Any, List
from cron_services.render_client import RenderAPIClient
from cron_services.dashboard_user_service import DashboardUserService
from cron_services.twilio_phone_service import TwilioPhoneService
from cron_models.cron_job import DealershipOnboard, EnvironmentVar
from datetime import datetime
import random
import logging

logger = logging.getLogger(__name__)


class DealershipOnboardService:
    def __init__(self):
        self.render_client = RenderAPIClient()
        self.user_service = DashboardUserService()
        self.twilio_service = TwilioPhoneService()

        # Standard environment variables for ALL dealerships
        self.standard_env_vars = {
            "DEBUG_MODE": "false",
            "ENHANCED_SYNC_ENABLED": "true",
            "OPENROUTER_API_KEY": "**",  # You'll want to replace with actual value
            "OPENROUTER_DEFAULT_MODEL": "anthropic/claude-3-5-sonnet-20241022",
            "PAGE_LOAD_TIMEOUT": "60",
            "POSTGRES_DB": "vautodb",
            "POSTGRES_HOST": "dpg-d2rna6be5dus73bvoe6g-a.oregon-postgres.render.com",
            "POSTGRES_PASSWORD": "gsUMCmAOQm63n6Fvkng77FflQSOwNdFT",
            "POSTGRES_PORT": "5432",
            "POSTGRES_USER": "vautodb_user",
            "SKIP_BOOK_VALUE_UPDATE": "false",
            "SKIP_DESCRIPTION_UPDATE": "false",
            "SKIP_FEATURES_UPDATE": "false",
            "SKIP_MEDIA_COUNT": "false",
            "TARGET_URL": "https://provision.vauto.app.coxautoinc.com/Va/Inventory/",
            "TWILIO_ACCOUNT_SID": "***",  # Replace with actual value
            "TWILIO_AUTH_TOKEN": "****",  # Replace with actual value
            "TWO_FACTOR_METHOD": "sms",
            "USE_VISION_AUTH": "true",
            "USE_VISION_CHECKBOXES": "true",
            "VEHICLE_ROW_INDEX": "1",
            "VIN_LOGIN_URL": "https://vauto.signin.coxautoinc.com"
        }

    def _generate_phone_number(self) -> str:
        """Generate a phone number for the dealership (DEPRECATED - use _get_or_purchase_phone_number)"""
        # Generate a random US phone number format +1XXXXXXXXXX
        area_code = random.randint(200, 999)  # Valid area codes start from 200
        exchange = random.randint(200, 999)   # Exchange codes start from 200
        number = random.randint(1000, 9999)   # Last four digits
        return f"+1{area_code}{exchange}{number}"

    async def _get_or_purchase_phone_number(self, dealership_name: str, job_type: str) -> str:
        """
        Get a real phone number for 2FA - either purchase new or use existing.

        Args:
            dealership_name: Name of dealership for friendly naming
            job_type: "AM" or "PM" for identification

        Returns:
            Phone number in E.164 format (e.g., "+15551234567")
        """
        if not self.twilio_service.is_configured():
            logger.warning("Twilio not configured, using generated fake number")
            return self._generate_phone_number()

        try:
            # Try to purchase a new number
            friendly_name = f"{dealership_name} {job_type}"
            result = await self.twilio_service.find_and_purchase_number(
                friendly_name=friendly_name
            )

            phone_number = result["phone_number"]
            logger.info(f"Purchased real phone number {phone_number} for {dealership_name} {job_type}")
            return phone_number

        except Exception as e:
            logger.warning(f"Failed to purchase phone number for {dealership_name}: {str(e)}")
            logger.info("Falling back to generated fake number")
            return self._generate_phone_number()

    def _parse_time_to_cron(self, time_str: str) -> str:
        """Parse time like '5:58AM' to cron format"""
        import re

        # Extract components from time string
        match = re.match(r'^(\d{1,2}):(\d{2})(AM|PM)$', time_str.upper())
        if not match:
            raise ValueError(f"Invalid time format: {time_str}")

        hour = int(match.group(1))
        minute = int(match.group(2))
        period = match.group(3)

        # Convert to 24-hour format
        if period == "PM" and hour != 12:
            hour += 12
        elif period == "AM" and hour == 12:
            hour = 0

        return f"{minute} {hour} * * *"

    def _calculate_schedule_time(self, time_period: str, existing_jobs: List[Dict[str, Any]]) -> str:
        """Calculate schedule time with slight variations for rate limiting (DEPRECATED - use _parse_time_to_cron instead)"""
        base_hour = 6 if time_period == "AM" else 18  # 6 AM or 6 PM UTC

        # Get existing schedules to avoid conflicts
        existing_times = []
        for job in existing_jobs:
            schedule = job.get("schedule", "")
            if schedule:
                # Extract minute from cron expression like "58 5 * * *"
                parts = schedule.split()
                if len(parts) >= 2:
                    try:
                        minute = int(parts[0])
                        hour = int(parts[1])
                        if hour == base_hour:  # Same base hour
                            existing_times.append(minute)
                    except ValueError:
                        continue

        # Generate a minute between 58-59 or 0-2 to spread load
        possible_minutes = [58, 59, 0, 1, 2]
        available_minutes = [m for m in possible_minutes if m not in existing_times]

        if not available_minutes:
            # If all slots taken, pick a random minute
            minute = random.randint(57, 3) % 60
        else:
            minute = random.choice(available_minutes)

        return f"{minute} {base_hour} * * *"

    def _build_dealership_environment_vars(self, onboard_data: DealershipOnboard, phone_number: str) -> List[Dict[str, str]]:
        """Build complete environment variables for dealership"""
        env_vars = []

        # Add all standard environment variables
        for key, value in self.standard_env_vars.items():
            env_vars.append({"key": key, "value": value})

        # Add dealership-specific variables
        env_vars.extend([
            {"key": "TWO_FACTOR_PHONE", "value": phone_number},
            {"key": "TWILIO_PHONE_NUMBER", "value": phone_number},
            {"key": "VAUTO_PASSWORD", "value": onboard_data.vauto_password},
            {"key": "VAUTO_USERNAME", "value": onboard_data.vauto_username},
            {"key": "ENVIRONMENT_ID", "value": onboard_data.vauto_username}
        ])

        return env_vars

    async def onboard_dealership(self, onboard_data: DealershipOnboard) -> Dict[str, Any]:
        """Complete dealership onboarding process - creates BOTH AM and PM jobs + dashboard user"""

        # Step 1: Validate user data first
        user_validation = await self.user_service.validate_user_data(onboard_data)
        if not user_validation["valid"]:
            return {
                "success": False,
                "error": "User validation failed",
                "conflicts": user_validation["conflicts"],
                "message": "Cannot create user account - conflicts detected"
            }

        # Step 2: Get or purchase one phone number for both jobs
        phone_number = await self._get_or_purchase_phone_number(onboard_data.dealership_name, "2FA")

        # Step 3: Parse time strings to cron schedules
        schedule_am = self._parse_time_to_cron(onboard_data.am_time)
        schedule_pm = self._parse_time_to_cron(onboard_data.pm_time)

        # Step 4: Create dashboard user first
        dashboard_user = await self.user_service.create_dashboard_user(onboard_data)

        # Step 5: Create both AM and PM jobs
        results = []

        # Create AM job
        am_service_name = f"{onboard_data.dealership_name} AM"
        am_env_vars = self._build_dealership_environment_vars(onboard_data, phone_number)

        am_payload = {
            "type": "cron_job",
            "name": am_service_name,
            "repo": "https://github.com/Allhaider-ai/zero-trust-python",
            "branch": "master",  # Based on your screenshot
            "schedule": schedule_am,
            "startCommand": "CMD",
            "envVars": am_env_vars,
            "runtime": "docker"
        }

        am_result = await self.render_client.create_cron_job(am_payload)
        results.append({
            "period": "AM",
            "service_id": am_result.get("id"),
            "service_name": am_service_name,
            "schedule": schedule_am,
            "phone_number": phone_number,
            "service_details": am_result
        })

        # Create PM job
        pm_service_name = f"{onboard_data.dealership_name} PM"
        pm_env_vars = self._build_dealership_environment_vars(onboard_data, phone_number)

        pm_payload = {
            "type": "cron_job",
            "name": pm_service_name,
            "repo": "https://github.com/Allhaider-ai/zero-trust-python",
            "branch": "master",
            "schedule": schedule_pm,
            "startCommand": "CMD",
            "envVars": pm_env_vars,
            "runtime": "docker"
        }

        pm_result = await self.render_client.create_cron_job(pm_payload)
        results.append({
            "period": "PM",
            "service_id": pm_result.get("id"),
            "service_name": pm_service_name,
            "schedule": schedule_pm,
            "phone_number": phone_number,
            "service_details": pm_result
        })

        return {
            "success": True,
            "dealership_name": onboard_data.dealership_name,
            "jobs_created": 2,
            "am_job": results[0],
            "pm_job": results[1],
            "dashboard_user": dashboard_user,
            "message": f"Successfully onboarded {onboard_data.dealership_name} with cron jobs and dashboard user",
            "all_results": results
        }

    async def get_next_available_slots(self, time_period: str) -> Dict[str, Any]:
        """Get next available time slots for scheduling"""
        existing_jobs = await self.render_client.list_services("cron_job")
        base_hour = 6 if time_period == "AM" else 18

        # Get existing schedules
        existing_times = []
        for job in existing_jobs:
            schedule = job.get("schedule", "")
            if schedule:
                parts = schedule.split()
                if len(parts) >= 2:
                    try:
                        minute = int(parts[0])
                        hour = int(parts[1])
                        if hour == base_hour:
                            existing_times.append(minute)
                    except ValueError:
                        continue

        # Show available slots
        possible_minutes = [58, 59, 0, 1, 2]
        available_minutes = [m for m in possible_minutes if m not in existing_times]

        return {
            "time_period": time_period,
            "base_hour": base_hour,
            "existing_slots": existing_times,
            "available_slots": available_minutes,
            "total_existing_jobs": len([j for j in existing_jobs if j.get("schedule", "").split()[1:2] == [str(base_hour)]])
        }

