from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from enum import Enum
import re


class EnvironmentVar(BaseModel):
    key: str
    value: str


class DealershipOnboard(BaseModel):
    """Simplified model for internal support team onboarding - creates BOTH AM and PM jobs + dashboard user"""
    dealership_name: str = Field(..., description="Dealership name (e.g., 'Kunes Ford Delavan')")
    vauto_username: str = Field(..., description="VAutoUsername from order email")
    vauto_password: str = Field(..., description="VAutoPassword from order email")
    am_time: str = Field(default="5:58AM", description="AM job time (e.g., '5:58AM', '6:02AM')")
    pm_time: str = Field(default="1:58PM", description="PM job time (e.g., '1:58PM', '6:02PM')")

    # Dashboard user fields
    dashboard_username: str = Field(..., description="Username for dashboard access")
    dashboard_password: str = Field(..., description="Password for dashboard access")
    dashboard_email: str = Field(..., description="Email for dashboard user")
    dashboard_first_name: str = Field(..., description="First name for dashboard user")
    dashboard_last_name: str = Field(..., description="Last name for dashboard user")
    dashboard_role: str = Field(default="dealership_user", description="Role for dashboard user")

    @field_validator('dealership_name')
    def validate_dealership_name(cls, v):
        if not v.strip():
            raise ValueError('dealership_name cannot be empty')
        return v.strip()

    @field_validator('dashboard_email')
    def validate_email(cls, v):
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v.lower().strip()

    @field_validator('dashboard_username')
    def validate_username(cls, v):
        if len(v.strip()) < 3:
            raise ValueError('Username must be at least 3 characters long')
        return v.strip().lower()

    @field_validator('dashboard_password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

    @field_validator('am_time', 'pm_time')
    def validate_time_format(cls, v: str) -> str:
        import re

        cleaned = v.strip().upper().replace(" ", "")
        time_pattern = r'^(0?[1-9]|1[0-2]):([0-5][0-9])(AM|PM)$'
        match = re.match(time_pattern, cleaned)
        if not match:
            raise ValueError('Time must be in format like "5:58AM" or "1:58PM"')

        hour = int(match.group(1))
        minute = match.group(2)
        period = match.group(3)
        return f"{hour}:{minute}{period}"


class CronJobCreate(BaseModel):
    name: str = Field(..., description="Name of the cron job")
    schedule: str = Field(..., description="Cron expression (e.g., '0 19 * * *' for 7:00 PM UTC)")
    repo_url: str = Field(..., description="GitHub repository URL")
    branch: str = Field(default="main", description="Git branch to use")
    start_command: str = Field(default="CMD", description="Command to run from Dockerfile")
    username: str = Field(..., description="Customer username")
    password: str = Field(..., description="Customer password")
    phone_number: str = Field(..., description="Customer phone number")
    additional_env_vars: Optional[List[EnvironmentVar]] = Field(
        default=None, description="Additional environment variables"
    )


class CronJobUpdate(BaseModel):
    name: Optional[str] = None
    schedule: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    phone_number: Optional[str] = None
    additional_env_vars: Optional[List[EnvironmentVar]] = None


class CronJobResponse(BaseModel):
    id: str
    name: str
    schedule: str
    status: str
    repo_url: str
    branch: str
    created_at: str
    updated_at: str


class CronJobRunResponse(BaseModel):
    id: str
    status: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    exit_code: Optional[int] = None


class ServiceListResponse(BaseModel):
    services: List[CronJobResponse]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None

