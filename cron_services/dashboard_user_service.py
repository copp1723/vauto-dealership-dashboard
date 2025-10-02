from typing import Dict, Any, Optional
import hashlib
import secrets
from datetime import datetime
from cron_models.cron_job import DealershipOnboard
from database import User, UserRole, VehicleDatabaseManager


class DashboardUserService:
    """Service for managing dashboard user creation."""

    def __init__(self):
        self.db_manager = VehicleDatabaseManager()

    def _hash_password(self, password: str) -> str:
        """Hash password for storage (simplified example)"""
        # In production, use proper password hashing like bcrypt
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return f"{salt}:{password_hash.hex()}"

    def _generate_user_id(self) -> str:
        """Generate unique user ID"""
        return f"usr_{secrets.token_hex(8)}"

    async def create_dashboard_user(self, onboard_data: DealershipOnboard) -> Dict[str, Any]:
        """Create a new dashboard user for the dealership in the database."""

        with self.db_manager.get_session() as session:
            # Map dashboard_role to UserRole enum
            role_map = {
                "dealership_user": UserRole.USER,
                "dealership_admin": UserRole.ADMIN,
                "admin": UserRole.ADMIN,
                "user": UserRole.USER
            }
            user_role = role_map.get(onboard_data.dashboard_role.lower(), UserRole.USER)

            # Create new user
            new_user = User(
                username=onboard_data.dashboard_username,
                role=user_role.value,
                is_active=True
            )
            new_user.set_password(onboard_data.dashboard_password)

            # Set empty store_ids for now (they can be assigned later by admins)
            new_user.set_store_ids([])

            session.add(new_user)
            session.commit()
            session.refresh(new_user)

            return {
                "success": True,
                "user_id": new_user.id,
                "username": new_user.username,
                "email": onboard_data.dashboard_email,  # Stored in form but not in DB
                "full_name": f"{onboard_data.dashboard_first_name} {onboard_data.dashboard_last_name}",
                "role": new_user.role_enum.value,
                "dealership": onboard_data.dealership_name,
                "created_at": new_user.created_at.isoformat(),
                "status": "active",
                "message": f"Dashboard user '{new_user.username}' created successfully for {onboard_data.dealership_name}. Email and name fields not stored (User model doesn't have these fields)."
            }

    async def validate_user_data(self, onboard_data: DealershipOnboard) -> Dict[str, Any]:
        """Validate that the user data doesn't conflict with existing users."""

        validation_results = {
            "valid": True,
            "conflicts": [],
            "warnings": []
        }

        with self.db_manager.get_session() as session:
            # Check if username already exists
            existing_user = session.query(User).filter(
                User.username == onboard_data.dashboard_username
            ).first()

            if existing_user:
                validation_results["valid"] = False
                validation_results["conflicts"].append({
                    "field": "username",
                    "value": onboard_data.dashboard_username,
                    "message": f"Username '{onboard_data.dashboard_username}' is already taken"
                })

        return validation_results

    async def get_user_template_data(self) -> Dict[str, Any]:
        """Get template data for user creation form"""
        return {
            "available_roles": [
                {"value": "dealership_user", "label": "Dealership User"},
                {"value": "dealership_admin", "label": "Dealership Administrator"},
                {"value": "manager", "label": "Manager"},
                {"value": "viewer", "label": "View Only"}
            ],
            "default_permissions": [
                "view_dealership_data",
                "view_reports",
                "manage_inventory",
                "view_cron_jobs"
            ],
            "password_requirements": {
                "min_length": 6,
                "require_uppercase": False,
                "require_lowercase": False,
                "require_numbers": False,
                "require_symbols": False
            },
            "username_requirements": {
                "min_length": 3,
                "allowed_characters": "letters, numbers, underscore, hyphen"
            }
        }

