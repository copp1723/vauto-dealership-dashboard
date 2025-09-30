import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class CronSettings:
    def __init__(self):
        self.render_api_key = os.getenv("RENDER_API_KEY", "")
        self.render_api_base_url = os.getenv("RENDER_API_BASE_URL", "https://api.render.com/v1")

        # Twilio configuration for phone number purchasing
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")

        # GitHub repository settings
        self.default_repo_url = os.getenv("DEFAULT_GITHUB_REPO", "https://github.com/example/dealership-automation")
        self.default_branch = os.getenv("DEFAULT_GITHUB_BRANCH", "main")

cron_settings = CronSettings()

