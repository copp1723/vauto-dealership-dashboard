import httpx
import logging
from typing import List, Dict, Optional
from cron_services.config import cron_settings as settings

logger = logging.getLogger(__name__)


class TwilioPhoneService:
    """Service for purchasing and managing Twilio phone numbers for 2FA"""

    def __init__(self):
        self.account_sid = getattr(settings, 'twilio_account_sid', None)
        self.auth_token = getattr(settings, 'twilio_auth_token', None)
        self.base_url = "https://api.twilio.com/2010-04-01"

        if not self.account_sid or not self.auth_token:
            logger.warning("Twilio credentials not configured - phone purchasing disabled")

    async def search_available_numbers(self,
                                     area_code: Optional[str] = None,
                                     limit: int = 10) -> List[Dict]:
        """
        Search for available US phone numbers.

        Args:
            area_code: Optional 3-digit area code (e.g., "312")
            limit: Maximum number of results to return

        Returns:
            List of available phone number dictionaries
        """
        if not self.account_sid or not self.auth_token:
            raise ValueError("Twilio credentials not configured")

        # Search for local US numbers
        url = f"{self.base_url}/Accounts/{self.account_sid}/AvailablePhoneNumbers/US/Local.json"

        params = {
            "SmsEnabled": "true",  # Must support SMS for 2FA
            "VoiceEnabled": "true",  # Optional but good to have
            "Limit": limit
        }

        # Add area code filter if specified
        if area_code:
            params["AreaCode"] = area_code

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    params=params,
                    auth=(self.account_sid, self.auth_token),
                    headers={"Accept": "application/json"}
                )
                response.raise_for_status()

                data = response.json()
                available_numbers = data.get("available_phone_numbers", [])

                logger.info(f"Found {len(available_numbers)} available numbers")
                return available_numbers

            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to search numbers: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Error searching numbers: {str(e)}")
                raise

    async def purchase_phone_number(self,
                                  phone_number: str,
                                  friendly_name: Optional[str] = None,
                                  sms_url: Optional[str] = None) -> Dict:
        """
        Purchase a phone number from Twilio.

        Args:
            phone_number: Full phone number in E.164 format (e.g., "+15551234567")
            friendly_name: Optional friendly name for the number
            sms_url: Optional webhook URL for SMS messages

        Returns:
            Dictionary with purchased number details
        """
        if not self.account_sid or not self.auth_token:
            raise ValueError("Twilio credentials not configured")

        url = f"{self.base_url}/Accounts/{self.account_sid}/IncomingPhoneNumbers.json"

        data = {
            "PhoneNumber": phone_number
        }

        if friendly_name:
            data["FriendlyName"] = friendly_name

        if sms_url:
            data["SmsUrl"] = sms_url
            data["SmsMethod"] = "POST"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    data=data,
                    auth=(self.account_sid, self.auth_token),
                    headers={"Accept": "application/json"}
                )
                response.raise_for_status()

                purchased_number = response.json()
                logger.info(f"Successfully purchased number: {phone_number}")

                return {
                    "phone_number": purchased_number.get("phone_number"),
                    "sid": purchased_number.get("sid"),
                    "friendly_name": purchased_number.get("friendly_name"),
                    "capabilities": purchased_number.get("capabilities", {}),
                    "status": "purchased"
                }

            except httpx.HTTPStatusError as e:
                error_details = e.response.text
                logger.error(f"Failed to purchase {phone_number}: {e.response.status_code} - {error_details}")

                # Parse Twilio error for better user feedback
                try:
                    error_data = e.response.json()
                    error_message = error_data.get("message", "Unknown error")
                    error_code = error_data.get("code")
                    raise ValueError(f"Twilio Error {error_code}: {error_message}")
                except:
                    raise ValueError(f"Failed to purchase number: {e.response.status_code}")

            except Exception as e:
                logger.error(f"Error purchasing number: {str(e)}")
                raise

    async def find_and_purchase_number(self,
                                     area_code: Optional[str] = None,
                                     friendly_name: Optional[str] = None) -> Dict:
        """
        Convenience method to find and purchase a number in one step.

        Args:
            area_code: Optional area code preference
            friendly_name: Optional name for the number

        Returns:
            Dictionary with purchased number details
        """
        # Search for available numbers
        available = await self.search_available_numbers(area_code=area_code, limit=5)

        if not available:
            area_msg = f" in area code {area_code}" if area_code else ""
            raise ValueError(f"No phone numbers available{area_msg}")

        # Take the first available number
        selected_number = available[0]
        phone_number = selected_number["phone_number"]

        logger.info(f"Selected number {phone_number} from {len(available)} available")

        # Purchase it
        return await self.purchase_phone_number(
            phone_number=phone_number,
            friendly_name=friendly_name or f"2FA Number - {phone_number}"
        )

    async def list_owned_numbers(self) -> List[Dict]:
        """
        List all phone numbers owned by the account.

        Returns:
            List of owned phone number dictionaries
        """
        if not self.account_sid or not self.auth_token:
            raise ValueError("Twilio credentials not configured")

        url = f"{self.base_url}/Accounts/{self.account_sid}/IncomingPhoneNumbers.json"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    auth=(self.account_sid, self.auth_token),
                    headers={"Accept": "application/json"}
                )
                response.raise_for_status()

                data = response.json()
                numbers = data.get("incoming_phone_numbers", [])

                return [
                    {
                        "phone_number": num.get("phone_number"),
                        "sid": num.get("sid"),
                        "friendly_name": num.get("friendly_name"),
                        "capabilities": num.get("capabilities", {}),
                        "date_created": num.get("date_created")
                    }
                    for num in numbers
                ]

            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to list numbers: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Error listing numbers: {str(e)}")
                raise

    def is_configured(self) -> bool:
        """Check if Twilio credentials are properly configured."""
        return bool(self.account_sid and self.auth_token)

