#!/usr/bin/env python3
"""
Vehicle Processing Database Module
SQLAlchemy models and database operations for tracking vehicle processing changes.
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, Column, String, DateTime, Text, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
from passlib.hash import bcrypt as bcrypt_hash
import enum

# Load environment variables
load_dotenv()

# Create base class for models
Base = declarative_base()

# Role enumeration for user access levels
class UserRole(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"  # Can access all stores, manage all users
    ADMIN = "ADMIN"             # Can access assigned stores
    USER = "USER"               # Can only access assigned single store


class User(Base):
    """User authentication model for dashboard access"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # Match actual database column
    role = Column(String(20), nullable=False, default=UserRole.USER.value, index=True)
    store_id = Column(String(100), nullable=True, index=True)
    store_ids = Column(Text, nullable=True)  # JSON string for multiple stores
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    created_by_id = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    def set_password(self, password: str):
        """Hash and set password using legacy SHA256 for compatibility"""
        self.password_hash = self._legacy_hash(password)

    def check_password(self, password: str) -> bool:
        """Check if provided password matches stored hash"""
        stored = self.password_hash or ""

        # Support accounts that were migrated to bcrypt during unauthorized changes
        if stored.startswith("$2"):
            try:
                return bcrypt_hash.verify(password, stored)
            except ValueError:
                pass

        # Fallback to original SHA256 hashing scheme
        return stored == self._legacy_hash(password)

    @staticmethod
    def _legacy_hash(password: str) -> str:
        """Legacy SHA256 hashing implementation"""
        return hashlib.sha256(password.encode()).hexdigest()

    def get_store_ids(self) -> List[str]:
        """Get list of accessible store IDs for this user"""
        if self.role == UserRole.SUPER_ADMIN.value:
            return []
        return [self.store_id] if self.store_id else []

    def set_store_ids(self, store_ids: List[str]):
        """Set accessible store IDs for this user"""
        if store_ids:
            self.store_id = store_ids[0]
        else:
            self.store_id = None

    def can_access_store(self, store_id: str) -> bool:
        """Check if user can access a specific store"""
        if self.role == UserRole.SUPER_ADMIN.value:
            return True
        return store_id == self.store_id

    def can_manage_user(self, target_user: 'User') -> bool:
        """Check if this user can manage (create/edit/delete) another user"""
        if self.role == UserRole.SUPER_ADMIN.value:
            return target_user.role != UserRole.SUPER_ADMIN.value

        if self.role == UserRole.ADMIN.value:
            # Admins can manage regular users assigned to the same store (if defined)
            if target_user.role == UserRole.USER.value:
                if not self.store_id or not target_user.store_id:
                    return True
                return self.store_id == target_user.store_id
        return False

    def get_role_display(self) -> str:
        """Get human-readable role name"""
        role_names = {
            UserRole.SUPER_ADMIN.value: "Super Administrator",
            UserRole.ADMIN.value: "Administrator",
            UserRole.USER.value: "User"
        }
        return role_names.get(self.role, str(self.role))

    @property
    def role_enum(self) -> UserRole:
        """Return the current role as a UserRole enum, defaulting to USER"""
        try:
            return UserRole(str(self.role).upper())
        except ValueError:
            return UserRole.USER

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'role_display': self.get_role_display(),
            'store_ids': self.get_store_ids(),
            'store_id': self.store_id,
            'created_by_id': None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': None
        }
    
    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}', store='{self.store_id}')>"


def build_postgres_url_from_env() -> str:
    """Build PostgreSQL database URL from environment variables without side effects."""
    postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
    postgres_port = os.getenv('POSTGRES_PORT', '5432')
    postgres_user = os.getenv('POSTGRES_USER')
    postgres_password = os.getenv('POSTGRES_PASSWORD')
    postgres_db = os.getenv('POSTGRES_DB', 'vehicle_processing')

    if not postgres_user or not postgres_password:
        raise ValueError(
            "PostgreSQL credentials are required. Please set POSTGRES_USER and POSTGRES_PASSWORD in your .env file.\n"
            "Required environment variables:\n"
            "- POSTGRES_USER\n"
            "- POSTGRES_PASSWORD\n"
            "- POSTGRES_DB (optional, defaults to 'vehicle_processing')\n"
            "- POSTGRES_HOST (optional, defaults to 'localhost')\n"
            "- POSTGRES_PORT (optional, defaults to '5432')"
        )

    return f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"

class VehicleProcessingRecord(Base):
    """Model to track vehicle processing changes and modifications"""
    __tablename__ = 'vehicle_processing_records'
    
    # Primary identifiers
    id = Column(Integer, primary_key=True, autoincrement=True)
    stock_number = Column(String(50), nullable=False, index=True)
    vin = Column(String(17), nullable=True, index=True)
    vehicle_name = Column(String(200), nullable=True, index=True)  # Vehicle year, make, model
    
    # Environment/Session identifiers for filtering
    environment_id = Column(String(100), nullable=True, index=True)  # Environment ID from .env file
    
    # Processing metadata
    processing_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    processing_session_id = Column(String(100), nullable=True)
    
    # Vehicle basic info
    odometer = Column(String(20), nullable=True)
    days_in_inventory = Column(String(10), nullable=True)
    
    # Description changes
    original_description = Column(Text, nullable=True)
    ai_generated_description = Column(Text, nullable=True)
    final_description = Column(Text, nullable=True)
    description_updated = Column(Boolean, default=False)
    
    # Features and modifications
    starred_features = Column(Text, nullable=True)  # JSON string of starred features
    marked_features_count = Column(Integer, default=0)
    feature_decisions = Column(Text, nullable=True)  # JSON string of LLM feature decisions
    
    # Certifications and special attributes
    no_fear_certificate = Column(Boolean, default=False)
    no_fear_certificate_text = Column(Text, nullable=True)
    
    # AI Analysis results
    ai_analysis_result = Column(Text, nullable=True)  # JSON string of full analysis
    screenshot_path = Column(String(500), nullable=True)
    
    # Processing status and results
    processing_status = Column(String(20), default='pending')  # pending, processing, completed, failed
    processing_successful = Column(Boolean, default=False)
    errors_encountered = Column(Text, nullable=True)  # JSON string of errors
    processing_duration = Column(String(20), nullable=True)  # Duration in seconds
    no_build_data_found = Column(Boolean, default=False)  # Flag for missing build data
    
    # Book Values and Media info
    book_values_processed = Column(Boolean, default=False)
    book_values_before_processing = Column(Text, nullable=True)  # JSON string of book values before processing
    book_values_after_processing = Column(Text, nullable=True)  # JSON string of book values after processing
    media_tab_processed = Column(Boolean, default=False)
    media_totals_found = Column(Text, nullable=True)  # JSON string of totals found
    
    def __repr__(self):
        return f"<VehicleProcessingRecord(stock_number='{self.stock_number}', processing_date='{self.processing_date}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary for easy serialization"""
        return {
            'id': self.id,
            'stock_number': self.stock_number,
            'vin': self.vin,
            'vehicle_name': self.vehicle_name,
            'environment_id': self.environment_id,
            'processing_date': self.processing_date.isoformat() if self.processing_date else None,
            'processing_session_id': self.processing_session_id,
            'odometer': self.odometer,
            'days_in_inventory': self.days_in_inventory,
            'original_description': self.original_description,
            'ai_generated_description': self.ai_generated_description,
            'final_description': self.final_description,
            'description_updated': self.description_updated,
            'starred_features': json.loads(self.starred_features) if self.starred_features else None,
            'marked_features_count': self.marked_features_count,
            'feature_decisions': json.loads(self.feature_decisions) if self.feature_decisions else None,
            'no_fear_certificate': self.no_fear_certificate,
            'no_fear_certificate_text': self.no_fear_certificate_text,
            'ai_analysis_result': json.loads(self.ai_analysis_result) if self.ai_analysis_result else None,
            'screenshot_path': self.screenshot_path,
            'processing_status': self.processing_status,
            'processing_successful': self.processing_successful,
            'errors_encountered': json.loads(self.errors_encountered) if self.errors_encountered else None,
            'processing_duration': self.processing_duration,
            'no_build_data_found': self.no_build_data_found,
            'book_values_processed': self.book_values_processed,
            'book_values_before_processing': json.loads(self.book_values_before_processing) if self.book_values_before_processing else None,
            'book_values_after_processing': json.loads(self.book_values_after_processing) if self.book_values_after_processing else None,
            'media_tab_processed': self.media_tab_processed,
            'media_totals_found': json.loads(self.media_totals_found) if self.media_totals_found else None,
        }


class VehicleDatabaseManager:
    """Database manager for vehicle processing operations"""
    
    def __init__(self, db_url: str = None):
        """Initialize database connection"""
        if db_url is None:
            db_url = self._get_database_url()
        
        self.db_url = db_url
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables if they don't exist
        self.create_tables()
    
    def _get_database_url(self) -> str:
        """Get PostgreSQL database URL from environment variables"""
        return build_postgres_url_from_env()
    
    def create_tables(self):
        """Create database tables"""
        try:
            Base.metadata.create_all(bind=self.engine)
            # Run user migration after creating tables
            self._migrate_users_if_needed()
        except Exception as e:
            print(f"Error creating database tables: {e}")
    
    def _migrate_users_if_needed(self):
        """Check if users need migration and perform it if necessary"""
        try:
            with self.get_session() as session:
                # Check if there are any users without roles (old schema)
                users_without_roles = session.query(User).filter(User.role.is_(None)).count()
                
                if users_without_roles > 0:
                    print(f"Found {users_without_roles} users that need migration...")
                    migrate_users_to_role_system(self)
                    
                # Check if we need to create the first super admin
                super_admins = session.query(User).filter(User.role == UserRole.SUPER_ADMIN.value).count()
                if super_admins == 0:
                    print("No super admin found. Creating default super admin...")
                    create_super_admin(self)
                    
        except Exception as e:
            print(f"Warning: Could not check user migration status: {e}")
            # This might happen on first run when tables don't exist yet
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def create_vehicle_record(
        self,
        stock_number: str,
        vin: str = None,
        vehicle_name: str = None,
        processing_session_id: str = None,
        odometer: str = None,
        days_in_inventory: str = None,
        environment_id: str = None
    ) -> Optional[VehicleProcessingRecord]:
        """Create a new vehicle processing record"""
        try:
            with self.get_session() as session:
                # Get environment_id from environment variable if not provided
                if environment_id is None:
                    environment_id = os.getenv('ENVIRONMENT_ID')
                
                record = VehicleProcessingRecord(
                    stock_number=stock_number,
                    vin=vin,
                    vehicle_name=vehicle_name,
                    environment_id=environment_id,
                    processing_session_id=processing_session_id,
                    odometer=odometer,
                    days_in_inventory=days_in_inventory,
                    processing_date=datetime.utcnow()
                )
                session.add(record)
                session.commit()
                session.refresh(record)
                print(f"Created vehicle processing record for stock #{stock_number}")
                return record
        except Exception as e:
            print(f"Error creating vehicle record: {e}")
            return None
    
    def update_vehicle_record(self, record_id: int, **kwargs) -> bool:
        """Update an existing vehicle processing record"""
        try:
            with self.get_session() as session:
                record = session.query(VehicleProcessingRecord).filter_by(id=record_id).first()
                if not record:
                    print(f"Vehicle record {record_id} not found")
                    return False
                
                # Update provided fields
                for key, value in kwargs.items():
                    if hasattr(record, key):
                        # Handle JSON fields
                        if key in ['starred_features', 'feature_decisions', 'ai_analysis_result', 'errors_encountered', 'media_totals_found', 'book_values_before_processing', 'book_values_after_processing']:
                            if value is not None and not isinstance(value, str):
                                value = json.dumps(value)
                        setattr(record, key, value)
                
                session.commit()
                print(f"Updated vehicle record {record_id} for stock #{record.stock_number}")
                return True
        except Exception as e:
            print(f"Error updating vehicle record: {e}")
            return False
    
    def get_vehicle_record_by_stock(self, stock_number: str) -> Optional[VehicleProcessingRecord]:
        """Get the most recent processing record for a stock number"""
        try:
            with self.get_session() as session:
                record = session.query(VehicleProcessingRecord).filter_by(
                    stock_number=stock_number
                ).order_by(VehicleProcessingRecord.processing_date.desc()).first()
                return record
        except Exception as e:
            print(f"Error getting vehicle record: {e}")
            return None
    
    def stock_number_exists(self, stock_number: str) -> bool:
        """Check if a stock number already exists in the database"""
        try:
            with self.get_session() as session:
                record = session.query(VehicleProcessingRecord).filter_by(
                    stock_number=stock_number
                ).first()
                return record is not None
        except Exception as e:
            print(f"Error checking stock number existence: {e}")
            return False
    
    def get_all_vehicle_records(self, limit: int = 100, environment_id: str = None) -> List[VehicleProcessingRecord]:
        """Get all vehicle processing records (most recent first)"""
        try:
            with self.get_session() as session:
                query = session.query(VehicleProcessingRecord)
                
                # Filter by environment_id if provided
                if environment_id:
                    query = query.filter(VehicleProcessingRecord.environment_id == environment_id)
                
                records = query.order_by(
                    VehicleProcessingRecord.processing_date.desc()
                ).limit(limit).all()
                return records
        except Exception as e:
            print(f"Error getting vehicle records: {e}")
            return []
    
    def get_records_by_environment(self, environment_id: str, limit: int = 100) -> List[VehicleProcessingRecord]:
        """Get all records for a specific environment ID"""
        return self.get_all_vehicle_records(limit=limit, environment_id=environment_id)
    
    def get_all_environment_ids(self) -> List[str]:
        """Get all unique environment IDs in the database"""
        try:
            with self.get_session() as session:
                result = session.query(VehicleProcessingRecord.environment_id).distinct().all()
                return [env_id[0] for env_id in result if env_id[0] is not None]
        except Exception as e:
            print(f"Error getting environment IDs: {e}")
            return []
    
    def log_processing_summary(
        self,
        stock_number: str,
        vin: str = None,
        odometer: str = None,
        days_in_inventory: str = None,
        starred_features: List[Dict] = None,
        description_data: Dict = None,
        no_fear_certificate: bool = False,
        no_fear_text: str = None,
        ai_analysis: Dict = None,
        screenshot_path: str = None,
        processing_successful: bool = True,
        errors: List[str] = None,
        processing_duration: str = None,
        session_id: str = None
    ) -> Optional[int]:
        """Log a complete processing summary to database"""
        try:
            # Create the record
            record = self.create_vehicle_record(
                stock_number=stock_number,
                vin=vin,
                processing_session_id=session_id,
                odometer=odometer,
                days_in_inventory=days_in_inventory
            )
            
            if not record:
                return None
            
            # Update with detailed information
            update_data = {
                'processing_successful': processing_successful,
                'processing_duration': processing_duration,
                'screenshot_path': screenshot_path,
                'no_fear_certificate': no_fear_certificate,
                'no_fear_certificate_text': no_fear_text,
            }
            
            # Handle starred features
            if starred_features:
                update_data['starred_features'] = starred_features
                update_data['marked_features_count'] = len(starred_features)
            
            # Handle description data
            if description_data:
                update_data.update({
                    'original_description': description_data.get('original'),
                    'ai_generated_description': description_data.get('ai_generated'),
                    'final_description': description_data.get('final'),
                    'description_updated': description_data.get('updated', False)
                })
            
            # Handle AI analysis
            if ai_analysis:
                update_data['ai_analysis_result'] = ai_analysis
            
            # Handle errors
            if errors:
                update_data['errors_encountered'] = errors
            
            # Update the record
            if self.update_vehicle_record(record.id, **update_data):
                print(f"Processing summary logged for stock #{stock_number}")
                return record.id
            else:
                return None
                
        except Exception as e:
            print(f"Error logging processing summary: {e}")
            return None
    
    def generate_processing_report(self, days: int = 7, environment_id: str = None) -> Dict[str, Any]:
        """Generate a processing report for the last N days"""
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            with self.get_session() as session:
                query = session.query(VehicleProcessingRecord).filter(
                    VehicleProcessingRecord.processing_date >= cutoff_date
                )
                
                # Filter by environment_id if provided
                if environment_id:
                    query = query.filter(VehicleProcessingRecord.environment_id == environment_id)
                
                records = query.all()
                
                total_processed = len(records)
                successful = sum(1 for r in records if r.processing_successful)
                with_descriptions = sum(1 for r in records if r.description_updated)
                with_no_fear = sum(1 for r in records if r.no_fear_certificate)
                total_features_marked = sum(r.marked_features_count or 0 for r in records)
                
                return {
                    'report_period_days': days,
                    'total_vehicles_processed': total_processed,
                    'successful_processing': successful,
                    'success_rate': f"{(successful/total_processed*100):.1f}%" if total_processed > 0 else "0%",
                    'descriptions_updated': with_descriptions,
                    'no_fear_certificates': with_no_fear,
                    'total_features_marked': total_features_marked,
                    'average_features_per_vehicle': f"{(total_features_marked/total_processed):.1f}" if total_processed > 0 else "0",
                    'recent_records': [r.to_dict() for r in records[:10]]
                }
        except Exception as e:
            print(f"Error generating processing report: {e}")
            return {}
    
    def print_recent_activity(self, limit: int = 10):
        """Print recent vehicle processing activity"""
        try:
            records = self.get_all_vehicle_records(limit=limit)
            
            if not records:
                print("No recent vehicle processing activity found")
                return
            
            print(f"\nRecent Vehicle Processing Activity (Last {len(records)} records)")
            print("="*80)
            
            for record in records:
                status = "SUCCESS" if record.processing_successful else "FAILED"
                features = f", {record.marked_features_count} features marked" if record.marked_features_count else ""
                no_fear = ", NO FEAR cert" if record.no_fear_certificate else ""
                desc_updated = ", description updated" if record.description_updated else ""
                
                print(f"Stock #{record.stock_number} - {record.processing_date.strftime('%Y-%m-%d %H:%M')} - {status}{features}{no_fear}{desc_updated}")
                
        except Exception as e:
            print(f"Error printing recent activity: {e}")


# Global database manager instance
_db_manager = None

def get_database_manager(db_url: str = None) -> VehicleDatabaseManager:
    """Get global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = VehicleDatabaseManager(db_url)
    return _db_manager


def main():
    """Example usage and testing"""
    # Initialize database
    db = get_database_manager()
    
    # Example: Log a processing summary
    record_id = db.log_processing_summary(
        stock_number="01T3626B",
        vin="5FNYF6H53GB046387",
        odometer="147,507",
        days_in_inventory="1",
        starred_features=[
            {"id": "feature_1", "text": "Heated Seats"},
            {"id": "feature_2", "text": "Navigation System"}
        ],
        description_data={
            "original": "Original description here",
            "ai_generated": "AI generated description here",
            "final": "Final enhanced description here",
            "updated": True
        },
        no_fear_certificate=True,
        no_fear_text="NO FEAR Certification details",
        processing_successful=True,
        processing_duration="45.2"
    )
    
    print(f"Created record ID: {record_id}")
    
    # Show recent activity
    db.print_recent_activity()
    
    # Generate report
    report = db.generate_processing_report(days=30)
    print(f"\nProcessing Report:")
    print(json.dumps(report, indent=2))


def migrate_users_to_role_system(db_manager):
    """
    Migrate existing users to the new role-based system.
    This function should be called once after updating the database schema.
    """
    print("Starting user migration to role-based system...")
    
    try:
        with db_manager.get_session() as session:
            # Get all existing users
            users = session.query(User).all()
            
            if not users:
                print("No existing users found to migrate.")
                return
            
            # Update existing users
            for user in users:
                if not getattr(user, 'role', None):
                    user.role = UserRole.USER.value
                else:
                    try:
                        # Normalize role casing to match enum
                        normalized_role = UserRole(str(user.role).upper()).value
                        user.role = normalized_role
                    except ValueError:
                        # Leave unknown roles untouched but log for visibility
                        print(f"Warning: Unrecognized role '{user.role}' for user {user.username}")

                if not hasattr(user, 'is_active') or user.is_active is None:
                    user.is_active = True

                print(f"Migrated user: {user.username} -> Role: {user.role}")
            
            session.commit()
            print(f"Successfully migrated {len(users)} users to role-based system.")
            
    except Exception as e:
        print(f"Error during user migration: {e}")
        raise


def create_super_admin(db_manager, username: str = "superadmin", password: str = "admin123"):
    """
    Create the first super admin user. This should be called during initial setup.
    """
    print(f"Creating super admin user: {username}")
    
    try:
        with db_manager.get_session() as session:
            # Check if this specific username already exists
            existing_user = session.query(User).filter(
                User.username == username
            ).first()
            
            if existing_user:
                print(f"User already exists: {existing_user.username}")
                return existing_user
            
            # Create new super admin
            super_admin = User(
                username=username,
                role=UserRole.SUPER_ADMIN.value,
                is_active=True
            )
            super_admin.set_password(password)
            
            session.add(super_admin)
            session.commit()
            
            print(f"Super admin created successfully: {username}")
            print(f"Default password: {password}")
            print("⚠️  IMPORTANT: Change the default password immediately after first login!")
            
            return super_admin
            
    except Exception as e:
        print(f"Error creating super admin: {e}")
        raise


if __name__ == "__main__":
    main()
