#!/usr/bin/env python3
"""
Dealership Dashboard - FastAPI Backend
Professional dashboard for vehicle processing database
"""

import os
import sys
import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Request, HTTPException, Query, Depends, Form, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.hash import bcrypt as bcrypt_hash

load_dotenv()

from database import get_database_manager, User, UserRole

# Store normalization helpers for consistent friendly naming across the app
STORE_TOKEN_REGEX = re.compile(
    r'(kunes|chevrolet|chevy|cadillac|buick|gmc|ford|toyota|honda|hyundai|kia|nissan|vw|volkswagen|mazda|subaru|chrysler|dodge|jeep|ram|cdjr|autogroup|auto|group|mercedesbenz|madcity|mitsubishi|lakegeneva|oakcreek|greenfield|elkhorn|delavan|delevan|macomb|morrison|mt|carroll|antioch|hope|madison|janesville|stoughton|rockford|platteville|sterling|oregon|sycamore|belvidere|galesburg|woodstock|quincy|davenport|eastmoline|la|crosse|monroe|milwaukee|[a-z]+)'
)

STORE_TOKEN_DISPLAY = {
    'kunes': 'Kunes',
    'chevrolet': 'Chevrolet',
    'chevy': 'Chevy',
    'cadillac': 'Cadillac',
    'buick': 'Buick',
    'gmc': 'GMC',
    'ford': 'Ford',
    'toyota': 'Toyota',
    'honda': 'Honda',
    'hyundai': 'Hyundai',
    'kia': 'Kia',
    'nissan': 'Nissan',
    'vw': 'VW',
    'volkswagen': 'Volkswagen',
    'mazda': 'Mazda',
    'subaru': 'Subaru',
    'chrysler': 'Chrysler',
    'dodge': 'Dodge',
    'jeep': 'Jeep',
    'ram': 'RAM',
    'cdjr': 'CDJR',
    'autogroup': 'Auto Group',
    'auto': 'Auto',
    'group': 'Group',
    'mercedesbenz': 'Mercedes-Benz',
    'madcity': 'Mad City',
    'mitsubishi': 'Mitsubishi',
    'lakegeneva': 'Lake Geneva',
    'oakcreek': 'Oak Creek',
    'greenfield': 'Greenfield',
    'elkhorn': 'Elkhorn',
    'delavan': 'Delavan',
    'delevan': 'Delavan',
    'devan': 'Delavan',  # Common misspelling in environment IDs
    'macomb': 'Macomb',
    'morrison': 'Morrison',
    'mt': 'Mt.',
    'carroll': 'Carroll',
    'antioch': 'Antioch',
    'hope': 'Hope',
    'madison': 'Madison',
    'janesville': 'Janesville',
    'stoughton': 'Stoughton',
    'rockford': 'Rockford',
    'platteville': 'Platteville',
    'sterling': 'Sterling',
    'oregon': 'Oregon',
    'sycamore': 'Sycamore',
    'belvidere': 'Belvidere',
    'galesburg': 'Galesburg',
    'woodstock': 'Woodstock',
    'quincy': 'Quincy',
    'davenport': 'Davenport',
    'eastmoline': 'East Moline',
    'la': 'La',
    'crosse': 'Crosse',
    'monroe': 'Monroe',
    'milwaukee': 'Milwaukee',
}

STORE_LOCATION_TOKENS = {
    'Lake Geneva',
    'Oak Creek',
    'Greenfield',
    'Elkhorn',
    'Delavan',
    'Macomb',
    'Morrison',
    'Mt.',
    'Carroll',
    'Antioch',
    'Hope',
    'Madison',
    'Janesville',
    'Stoughton',
    'Rockford',
    'Platteville',
    'Sterling',
    'Oregon',
    'Sycamore',
    'Belvidere',
    'Galesburg',
    'Woodstock',
    'Quincy',
    'Davenport',
    'East Moline',
    'La',
    'Crosse',
    'Monroe',
    'Milwaukee',
}

STORE_ID_OVERRIDES = {
    'kunesautogroupmacomb': 'Kunes Auto Group Macomb',
    'kunesautogroupmorrison': 'Kunes Auto Group Morrison',
    'kunesautogroupmtcarroll': 'Kunes Auto Group Mt. Carroll',
    'kunesmadcitymitsubishi': 'Kunes Mad City Mitsubishi',
    'kunesmercedesbenzsycamore': 'Kunes Mercedes-Benz Sycamore',
    'kunesautogrouporegon': 'Kunes Auto Group Oregon',
    'kunesautogroupsycamore': 'Kunes Auto Group Sycamore',
    'kunesautogroupbelvidere': 'Kunes Auto Group Belvidere',
    'kunesautogroupgalesburg': 'Kunes Auto Group Galesburg',
    'kunesautogroupwoodstock': 'Kunes Auto Group Woodstock',
    'kunesautogroupquincy': 'Kunes Auto Group Quincy',
    'kunesautogroupdavenport': 'Kunes Auto Group Davenport',
    'kunesautogroupeastmoline': 'Kunes Auto Group East Moline',
}


def get_friendly_store_label(store_id: Optional[str]) -> str:
    """Generate a human-friendly store name from an environment/store identifier."""
    if not store_id:
        return "All Stores"

    slug = store_id.replace('-', '').replace('_', '').lower()

    if slug in STORE_ID_OVERRIDES:
        return STORE_ID_OVERRIDES[slug]

    tokens = STORE_TOKEN_REGEX.findall(slug)

    if not tokens:
        return store_id

    resolved_tokens: List[str] = []
    for token in tokens:
        resolved = STORE_TOKEN_DISPLAY.get(token, token.capitalize())
        resolved_tokens.append(resolved)

    if not resolved_tokens:
        return store_id

    # Separate brand descriptors from location descriptors for clearer phrasing
    brand_parts: List[str] = []
    location_parts: List[str] = []

    for part in resolved_tokens:
        if part in STORE_LOCATION_TOKENS:
            location_parts.append(part)
        else:
            brand_parts.append(part)

    if not brand_parts:
        brand_parts = resolved_tokens

    label = " ".join(dict.fromkeys(brand_parts))  # Preserve order, remove duplicates

    if location_parts:
        label = f"{label} of {' '.join(dict.fromkeys(location_parts))}"

    return label.strip()

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security
security = HTTPBearer()

# Pydantic Models for API responses
class VehicleInfo(BaseModel):
    id: int
    name: str
    stock_number: str
    vehicle_name: Optional[str] = None
    vin: Optional[str] = None
    odometer: Optional[str] = None
    days_in_inventory: Optional[str] = None
    processing_date: str
    processing_date_raw: Optional[str] = None
    status: str
    status_class: str
    processing_status: str
    processing_successful: bool
    description_status: str
    description_class: str
    description_updated: bool
    features_count: int
    features_text: str
    no_fear_certificate: bool
    special_features: List[str]
    processing_duration: Optional[str] = None
    has_errors: bool
    final_description: Optional[str] = None
    no_build_data_found: bool
    # Enhanced status information
    book_values_processed: bool
    media_tab_processed: bool
    book_values_status: str
    media_status: str
    processing_completeness: str
    processing_completeness_class: str

class PaginationInfo(BaseModel):
    page: int
    per_page: int
    total: int
    pages: int
    has_prev: bool
    has_next: bool

class VehiclesResponse(BaseModel):
    success: bool
    vehicles: List[VehicleInfo]
    pagination: PaginationInfo

class VehicleDetail(BaseModel):
    id: int
    stock_number: str
    vehicle_name: Optional[str] = None
    vin: Optional[str] = None
    odometer: Optional[str] = None
    days_in_inventory: Optional[str] = None
    processing_date: Optional[str] = None
    processing_status: str
    processing_successful: bool
    processing_duration: Optional[str] = None
    original_description: Optional[str] = None
    ai_generated_description: Optional[str] = None
    final_description: Optional[str] = None
    description_updated: bool
    starred_features: Optional[List[Dict[str, Any]]] = None
    starred_features_summary: Optional[str] = None
    marked_features_count: int
    feature_decisions: Optional[Dict[str, Any]] = None
    feature_decisions_summary: Optional[str] = None
    no_fear_certificate: bool
    no_fear_certificate_text: Optional[str] = None
    book_values_processed: bool
    book_values_before_processing: Optional[Dict[str, Any]] = None
    book_values_after_processing: Optional[Dict[str, Any]] = None
    media_tab_processed: bool
    media_totals_found: Optional[Dict[str, Any]] = None
    ai_analysis_result: Optional[Dict[str, Any]] = None
    errors_encountered: Optional[List[str]] = None
    screenshot_path: Optional[str] = None
    no_build_data_found: bool

class VehicleDetailResponse(BaseModel):
    success: bool
    vehicle: VehicleDetail

class Statistics(BaseModel):
    total_vehicles: int
    successful_processing: int
    success_rate: str
    success_rate_value: float
    descriptions_updated: int
    no_fear_certificates: int
    recent_activity_7_days: int
    total_features_marked: int
    avg_features_per_vehicle: str
    # New metrics
    total_book_value_mtd: float
    total_book_value_ytd: float
    book_value_insights_mtd: Dict[str, Any]
    book_value_insights_ytd: Dict[str, Any]
    time_saved_minutes: int
    time_saved_formatted: str

class StatisticsResponse(BaseModel):
    success: bool
    statistics: Statistics

class ActivityItem(BaseModel):
    id: int
    stock_number: str
    action: str
    time_ago: str
    processing_successful: bool
    processing_date: Optional[str] = None

class ActivityResponse(BaseModel):
    success: bool
    activity: List[ActivityItem]

class ErrorResponse(BaseModel):
    success: bool = False
    error: str

# Authentication Models
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    role: str = Field(..., description="User role: super_admin, admin, or user")
    store_ids: List[str] = Field(default=[], description="List of accessible store IDs")
    store_id: Optional[str] = Field(None, description="Deprecated: use store_ids instead")

class AdminUserCreate(BaseModel):
    """Model for creating users by admins - excludes role selection for security"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    store_ids: List[str] = Field(..., description="List of accessible store IDs")

class UserUpdate(BaseModel):
    """Model for updating user details"""
    password: Optional[str] = Field(None, min_length=6, description="New password (optional)")
    role: Optional[str] = Field(None, description="User role: admin or user")
    store_ids: Optional[List[str]] = Field(None, description="List of accessible store IDs")
    is_active: Optional[bool] = Field(None, description="User active status")

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Optional["UserResponse"] = None

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    role_display: str
    store_ids: List[str]
    store_id: Optional[str] = None  # Backward compatibility
    created_by_id: Optional[int] = None
    is_active: bool
    created_at: str
    last_login: Optional[str] = None

class UserListItem(BaseModel):
    """Simplified user info for lists"""
    id: int
    username: str
    role: str
    role_display: str
    store_ids: List[str]
    is_active: bool
    created_at: str
    last_login: Optional[str] = None

class StoreSelection(BaseModel):
    """Model for super admin store selection"""
    store_id: str = Field(..., description="Selected store ID for filtering")

class UserManagementResponse(BaseModel):
    """Response model for user management operations"""
    success: bool
    message: str
    user: Optional[UserResponse] = None

# Initialize FastAPI app
app = FastAPI(
    title="Dealership Dashboard API",
    description="Professional dashboard for vehicle processing database",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize templates
templates = Jinja2Templates(directory="templates")
# Include Cron Management API routes
from cron_routes import router as cron_router
app.include_router(cron_router)


# Initialize database manager (will use environment variables for database connection)
print("Initializing database connection...")
db_manager = get_database_manager()
if SECRET_KEY.startswith("your-secret-key-change-in-production"):
    print("⚠️ WARNING: Using default SECRET_KEY. Set SECRET_KEY in your .env so JWT tokens remain valid across restarts.")

# Check for super admin on startup
try:
    with db_manager.get_session() as session:
        super_admin_count = session.query(User).filter(User.role == UserRole.SUPER_ADMIN.value).count()
        if super_admin_count == 0:
            print("⚠️ WARNING: No super admin user found!")
            print("🔧 Run 'python setup_admin.py' to create the first super admin user.")
            print("   Or use the database migration functions to set up users.")
except Exception as e:
    print(f"⚠️ Could not check for super admin: {e}")
    print("🔧 Run 'python setup_admin.py' to initialize the system.")

# Authentication Helper Functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    if not hashed_password:
        return False

    if hashed_password.startswith("$2"):
        try:
            return bcrypt_hash.verify(plain_password, hashed_password)
        except ValueError:
            return False

    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

def get_password_hash(password: str) -> str:
    """Hash a plain password"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def authenticate_user(username: str, password: str):
    """Authenticate user with username and password"""
    with db_manager.get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if not user:
            return False
        if not user.check_password(password):
            return False
        return user

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token_value = credentials.credentials
        if not token_value:
            raise credentials_exception
        print(f"Auth Debug: got Authorization Bearer token of length {len(token_value)}")
        payload = jwt.decode(token_value, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        print(f"Auth Debug: token sub={username}")
    except JWTError as e:
        print(f"JWT Error: {e}")
        raise credentials_exception

    with db_manager.get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        if user is None or not user.is_active:
            raise credentials_exception
        return user

# Role-Based Access Control Functions
def require_role(required_roles: List[UserRole]):
    """Decorator to require specific user roles"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract current_user from kwargs if it exists
            current_user = kwargs.get('current_user')
            if not current_user:
                # Try to get from function signature
                for arg in args:
                    if isinstance(arg, User):
                        current_user = arg
                        break

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required roles: {[role.value for role in required_roles]}"
                )

            current_role = current_user.role_enum if hasattr(current_user, "role_enum") else UserRole(str(current_user.role).upper())

            if current_role not in required_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required roles: {[role.value for role in required_roles]}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator

def get_current_super_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure current user is super admin"""
    if current_user.role_enum != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user

def get_current_admin_or_higher(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure current user is admin or super admin"""
    if current_user.role_enum not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or super admin access required"
        )
    return current_user

def get_accessible_store_ids(current_user: User, selected_store_id: Optional[str] = None) -> List[str]:
    """Get list of store IDs that the current user can access"""
    if current_user.role_enum == UserRole.SUPER_ADMIN:
        if selected_store_id:
            # Super admin has selected a specific store
            return [selected_store_id]
        else:
            # Return empty list to indicate "all stores" access
            return []
    else:
        # Admin and User roles have limited store access
        if selected_store_id and selected_store_id in current_user.get_store_ids():
            # User has selected a specific store they have access to
            return [selected_store_id]
        else:
            # Return all accessible stores
            return current_user.get_store_ids()

def apply_store_filter(query, current_user: User, selected_store_id: Optional[str] = None):
    """Apply store-based filtering to a query based on user role and permissions"""
    from database import VehicleProcessingRecord

    print(f"DEBUG apply_store_filter: user_role={current_user.role}, selected_store_id={selected_store_id}")
    accessible_stores = get_accessible_store_ids(current_user, selected_store_id)
    print(f"DEBUG apply_store_filter: accessible_stores={accessible_stores}")

    if accessible_stores:
        # User has specific store access - filter by those stores
        print(f"DEBUG apply_store_filter: Filtering by specific stores: {accessible_stores}")
        return query.filter(VehicleProcessingRecord.environment_id.in_(accessible_stores))
    elif current_user.role_enum == UserRole.SUPER_ADMIN and not selected_store_id:
        # Super admin with no specific store selected - access all stores
        print(f"DEBUG apply_store_filter: Super admin with no store filter - returning all vehicles")
        return query  # No filtering needed
    else:
        # Fallback to old behavior for backward compatibility
        print(f"DEBUG apply_store_filter: Fallback case - user.store_id={current_user.store_id}")
        if current_user.store_id:
            return query.filter(VehicleProcessingRecord.environment_id == current_user.store_id)
        else:
            # No store filtering for this user - return all vehicles
            print(f"DEBUG apply_store_filter: No store restrictions - returning all vehicles")
            return query

# Helper Functions for Statistics
def calculate_book_value_difference(before_data: Dict, after_data: Dict) -> float:
    """Calculate the difference between before and after book values using KBB as primary"""
    try:
        before_kbb = parse_currency_value(before_data.get('KBB', '0')) if before_data else 0.0
        after_kbb = parse_currency_value(after_data.get('KBB', '0')) if after_data else 0.0

        # If no KBB, try other major sources
        if before_kbb == 0 and after_kbb == 0:
            for source in ['rBook', 'J.D. Power', 'MMR', 'Black Book']:
                before_val = parse_currency_value(before_data.get(source, '0')) if before_data else 0.0
                after_val = parse_currency_value(after_data.get(source, '0')) if after_data else 0.0
                if before_val > 0 or after_val > 0:
                    return after_val - before_val

        return after_kbb - before_kbb
    except (ValueError, TypeError, KeyError):
        return 0.0

def parse_currency_value(value_str: str) -> float:
    """Parse currency string like '$25,000' to float"""
    if not value_str or value_str.strip() == "":
        return 0.0
    try:
        # Remove $ signs, commas, and convert to float
        cleaned = value_str.replace('$', '').replace(',', '').strip()
        return float(cleaned) if cleaned else 0.0
    except (ValueError, TypeError):
        return 0.0

def calculate_book_value_insights(before_data: Dict, after_data: Dict) -> Dict:
    """Calculate detailed book value insights with category-by-category analysis"""
    insights = {
        'total_difference': 0.0,
        'categories': {},
        'best_improvement': {'category': '', 'amount': 0.0, 'details': None},
        'primary_source': 'KBB',
        'summary': 'No data available'
    }

    try:
        if not before_data or not after_data:
            return insights

        # Common book value categories we expect to see
        all_categories = set()
        if isinstance(before_data, dict):
            all_categories.update(before_data.keys())
        if isinstance(after_data, dict):
            all_categories.update(after_data.keys())

        # Remove empty string keys
        all_categories.discard('')

        best_improvement = 0.0
        best_category = ''
        primary_diff = 0.0

        # Calculate differences for each category
        for category in all_categories:
            if not category:  # Skip empty categories
                continue

            before_val = parse_currency_value(before_data.get(category, '0'))
            after_val = parse_currency_value(after_data.get(category, '0'))

            # Enhanced filtering logic to exclude initial merchandising
            # Only include legitimate changes (both values exist and are non-zero)
            # This excludes initial merchandising (0 -> value) which isn't automation impact
            if (before_val is None or after_val is None or
                before_val == 0.0 or after_val == 0.0 or
                before_val <= 0 or after_val <= 0):
                continue

            difference = after_val - before_val

            insights['categories'][category] = {
                'before': before_val,
                'after': after_val,
                'difference': difference,
                'improvement': difference > 0,
            }

            # Track best improvement
            if difference > best_improvement:
                best_improvement = difference
                best_category = category

            # Use KBB as primary, fallback to others
            if category == 'KBB':
                primary_diff = difference
                insights['primary_source'] = 'KBB'
            elif primary_diff == 0 and category in ['rBook', 'J.D. Power', 'MMR']:
                primary_diff = difference
                insights['primary_source'] = category

        insights['total_difference'] = primary_diff
        insights['best_improvement'] = {
            'category': best_category,
            'amount': best_improvement,
            'details': None
        }

        # Create summary
        if primary_diff > 0:
            insights['summary'] = f"${primary_diff:,.0f} increase found by automation"
        elif primary_diff < 0:
            insights['summary'] = f"${abs(primary_diff):,.0f} decrease found by automation"
        else:
            insights['summary'] = "No value change detected"

    except Exception as e:
        print(f"Error calculating book value insights: {e}")

    return insights


def aggregate_book_value_insights_for_period(vehicles: List[Any]) -> tuple[float, Dict[str, Any]]:
    """Aggregate book value insights across a collection of vehicles with top-change tracking."""
    insights: Dict[str, Any] = {
        'total_difference': 0.0,
        'categories': {},
        'best_improvement': {'category': '', 'amount': 0.0, 'details': None},
        'primary_source': 'KBB',
        'summary': 'No data available'
    }

    total_difference = 0.0
    best_positive_category = ''
    best_positive_amount = 0.0
    best_positive_details: Optional[Dict[str, Any]] = None

    best_absolute_category = ''
    best_absolute_amount = 0.0
    best_absolute_details: Optional[Dict[str, Any]] = None

    for vehicle in vehicles:
        try:
            before_raw = getattr(vehicle, 'book_values_before_processing', None)
            after_raw = getattr(vehicle, 'book_values_after_processing', None)
            before_data = json.loads(before_raw) if before_raw else {}
            after_data = json.loads(after_raw) if after_raw else {}
        except (json.JSONDecodeError, TypeError):
            continue

        if not before_data or not after_data:
            continue

        if hasattr(vehicle, 'vehicle_name') and vehicle.vehicle_name:
            vehicle_label = vehicle.vehicle_name
        elif hasattr(vehicle, 'name') and vehicle.name:
            vehicle_label = vehicle.name
        elif getattr(vehicle, 'stock_number', None):
            vehicle_label = f"Stock #{vehicle.stock_number}"
        else:
            vehicle_label = 'Vehicle'

        vehicle_insights = calculate_book_value_insights(before_data, after_data)
        difference_aggregate = calculate_book_value_difference(before_data, after_data)
        total_difference += difference_aggregate

        for category, data in vehicle_insights['categories'].items():
            category_entry = insights['categories'].setdefault(category, {
                'difference': 0.0,
                'before_total': 0.0,
                'after_total': 0.0,
                'improvement': False,
                'top_increase': None,
                'top_absolute': None
            })

            difference_value = float(round(data['difference'], 2))
            before_value = float(round(data['before'], 2))
            after_value = float(round(data['after'], 2))

            category_entry['difference'] += difference_value
            category_entry['before_total'] += before_value
            category_entry['after_total'] += after_value

            detail = {
                'vehicle_name': vehicle_label,
                'stock_number': getattr(vehicle, 'stock_number', None),
                'amount': difference_value,
                'before': before_value,
                'after': after_value
            }

            if difference_value > 0:
                category_entry['improvement'] = True
                top_increase = category_entry.get('top_increase')
                if not top_increase or difference_value > top_increase['amount']:
                    category_entry['top_increase'] = detail

                if difference_value > best_positive_amount:
                    best_positive_amount = difference_value
                    best_positive_category = category
                    best_positive_details = detail

            top_absolute = category_entry.get('top_absolute')
            if abs(difference_value) > 0:
                if not top_absolute or abs(difference_value) > abs(top_absolute['amount']):
                    category_entry['top_absolute'] = detail

                if (best_absolute_details is None) or abs(difference_value) > abs(best_absolute_amount):
                    best_absolute_amount = difference_value
                    best_absolute_category = category
                    best_absolute_details = detail

    filtered_categories: Dict[str, Any] = {}
    for category, data in insights['categories'].items():
        difference = data.get('difference', 0.0)
        if abs(difference) < 1e-6:
            continue

        data['difference'] = float(round(difference, 2))
        data['before_total'] = float(round(data.get('before_total', 0.0), 2))
        data['after_total'] = float(round(data.get('after_total', 0.0), 2))

        filtered_categories[category] = {
            'difference': data['difference'],
            'before_total': data['before_total'],
            'after_total': data['after_total']
        }

    insights['categories'] = filtered_categories
    insights['total_difference'] = float(round(total_difference, 2))

    if best_positive_category:
        insights['primary_source'] = best_positive_category
        insights['best_improvement'] = {
            'category': best_positive_category,
            'amount': float(round(best_positive_amount, 2)),
            'details': best_positive_details
        }
    elif best_absolute_category:
        insights['primary_source'] = best_absolute_category
        insights['best_improvement'] = {
            'category': best_absolute_category,
            'amount': float(round(best_absolute_amount, 2)),
            'details': best_absolute_details
        }
    else:
        insights['best_improvement'] = {
            'category': '',
            'amount': 0.0,
            'details': None
        }

    if total_difference > 0:
        insights['summary'] = f"${total_difference:,.0f} total increase"
    elif total_difference < 0:
        insights['summary'] = f"${abs(total_difference):,.0f} total decrease"
    else:
        insights['summary'] = "No value changes detected"

    return insights['total_difference'], insights

def calculate_time_saved(vehicle_count: int) -> tuple[int, str]:
    """Calculate time saved based on vehicle count (11 minutes per vehicle)"""
    total_minutes = vehicle_count * 11
    hours = total_minutes // 60
    minutes = total_minutes % 60

    if hours > 0:
        formatted = f"{hours} hour{'s' if hours != 1 else ''}"
    elif minutes > 0:
        formatted = f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        formatted = "0"

    return total_minutes, formatted

def get_month_start() -> datetime:
    """Get the start of the current month"""
    now = datetime.utcnow()
    return datetime(now.year, now.month, 1)

def get_year_start() -> datetime:
    """Get the start of the current year"""
    now = datetime.utcnow()
    return datetime(now.year, 1, 1)

# Quick check to see if we can access data
try:
    with db_manager.get_session() as session:
        from database import VehicleProcessingRecord
        count = session.query(VehicleProcessingRecord).count()
        print(f"📊 Found {count} vehicle records in database")
except Exception as e:
    print(f"⚠️ Error accessing database: {e}")

# Authentication Routes
# Note: Public signup removed - users must be created by admins

@app.post("/api/login", response_model=Token)
async def login(user_data: UserLogin):
    """User login endpoint"""
    try:
        user = authenticate_user(user_data.username, user_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create proper JWT access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )

        # Return token with user info
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user.id,
                username=user.username,
                role=user.role_enum.value,
                role_display=user.get_role_display(),
                store_ids=user.get_store_ids(),
                store_id=user.store_id,
                created_by_id=None,
                is_active=user.is_active,
                created_at=user.created_at.isoformat(),
                last_login=None
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during login: {str(e)}"
        )

@app.get("/api/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role_enum.value,
        role_display=current_user.get_role_display(),
        store_ids=current_user.get_store_ids(),
        store_id=current_user.store_id,
        created_by_id=None,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat(),
        last_login=None
    )

# User Management Routes

@app.post("/api/admin/users", response_model=UserManagementResponse)
async def create_user_by_admin(
    user_data: AdminUserCreate,
    current_user: User = Depends(get_current_admin_or_higher)
):
    """Create a new user (admin-only endpoint)"""
    try:
        with db_manager.get_session() as session:
            # Check if username already exists
            existing_user = session.query(User).filter(User.username == user_data.username).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered"
                )

            # Determine the role for the new user based on current user's role
            if current_user.role_enum == UserRole.SUPER_ADMIN:
                # Super admin can create admins and users, default to user
                new_role = UserRole.USER
            elif current_user.role_enum == UserRole.ADMIN:
                # Admin can only create users
                new_role = UserRole.USER
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to create users"
                )

            # For admin users, validate they can only assign stores they have access to
            if current_user.role_enum == UserRole.ADMIN:
                admin_stores = current_user.get_store_ids()
                invalid_stores = [store_id for store_id in user_data.store_ids if store_id not in admin_stores]
                if invalid_stores:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"You don't have access to these stores: {', '.join(invalid_stores)}. You can only assign stores you have access to: {', '.join(admin_stores)}"
                    )

            # Create new user
            new_user = User(
                username=user_data.username,
                role=new_role.value,
                is_active=True
            )
            new_user.set_password(user_data.password)
            new_user.set_store_ids(user_data.store_ids)

            session.add(new_user)
            session.commit()
            session.refresh(new_user)

            return UserManagementResponse(
                success=True,
                message=f"User {new_user.username} created successfully",
                user=UserResponse(
                    id=new_user.id,
                    username=new_user.username,
                    role=new_user.role_enum.value,
                    role_display=new_user.get_role_display(),
                    store_ids=new_user.get_store_ids(),
                    store_id=new_user.store_id,
                    created_by_id=None,
                    is_active=new_user.is_active,
                    created_at=new_user.created_at.isoformat(),
                    last_login=None
                )
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )

@app.post("/api/superadmin/admins", response_model=UserManagementResponse)
async def create_admin_by_superadmin(
    user_data: UserCreate,
    current_user: User = Depends(get_current_super_admin)
):
    """Create a new admin user (super admin only)"""
    try:
        with db_manager.get_session() as session:
            # Check if username already exists
            existing_user = session.query(User).filter(User.username == user_data.username).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered"
                )

            # Validate role
            try:
                role_enum = UserRole(user_data.role.upper())
                if role_enum not in [UserRole.ADMIN, UserRole.USER]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Super admin can only create admin or user accounts"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid role. Valid roles: admin, user"
                )

            # Create new user
            new_user = User(
                username=user_data.username,
                role=role_enum.value,
                is_active=True
            )
            new_user.set_password(user_data.password)

            # Set store IDs
            if user_data.store_ids:
                new_user.set_store_ids(user_data.store_ids)
            elif user_data.store_id:  # Backward compatibility
                new_user.set_store_ids([user_data.store_id])

            session.add(new_user)
            session.commit()
            session.refresh(new_user)

            return UserManagementResponse(
                success=True,
                message=f"Admin user {new_user.username} created successfully",
                user=UserResponse(
                    id=new_user.id,
                    username=new_user.username,
                    role=new_user.role_enum.value,
                    role_display=new_user.get_role_display(),
                    store_ids=new_user.get_store_ids(),
                    store_id=new_user.store_id,
                    created_by_id=None,
                    is_active=new_user.is_active,
                    created_at=new_user.created_at.isoformat(),
                    last_login=None
                )
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating admin user: {str(e)}"
        )

@app.get("/api/admin/users", response_model=List[UserListItem])
async def list_managed_users(current_user: User = Depends(get_current_admin_or_higher)):
    """List users that the current admin can manage"""
    try:
        with db_manager.get_session() as session:
            if current_user.role_enum == UserRole.SUPER_ADMIN:
                # Super admin can see all users except other super admins
                users = session.query(User).filter(User.role != UserRole.SUPER_ADMIN.value).all()
            else:
                # Admins can view regular users associated with their store
                query = session.query(User).filter(User.role == UserRole.USER.value)
                if current_user.store_id:
                    query = query.filter(User.store_id == current_user.store_id)
                users = query.all()

            return [
                UserListItem(
                    id=user.id,
                    username=user.username,
                    role=user.role_enum.value,
                    role_display=user.get_role_display(),
                    store_ids=user.get_store_ids(),
                    is_active=user.is_active,
                    created_at=user.created_at.isoformat(),
                    last_login=None
                ) for user in users
            ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing users: {str(e)}"
        )

@app.delete("/api/admin/users/{user_id}", response_model=UserManagementResponse)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin_or_higher)
):
    """Delete a user (admin can only delete users they created)"""
    try:
        with db_manager.get_session() as session:
            target_user = session.query(User).filter(User.id == user_id).first()

            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            # Check permissions
            if not current_user.can_manage_user(target_user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to delete this user"
                )

            username = target_user.username
            session.delete(target_user)
            session.commit()

            return UserManagementResponse(
                success=True,
                message=f"User {username} deleted successfully"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )

@app.put("/api/admin/users/{user_id}/toggle-active", response_model=UserManagementResponse)
async def toggle_user_active(
    user_id: int,
    current_user: User = Depends(get_current_admin_or_higher)
):
    """Toggle user active status"""
    try:
        with db_manager.get_session() as session:
            target_user = session.query(User).filter(User.id == user_id).first()

            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            # Check permissions
            if not current_user.can_manage_user(target_user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to modify this user"
                )

            target_user.is_active = not target_user.is_active
            session.commit()

            status_text = "activated" if target_user.is_active else "deactivated"
            return UserManagementResponse(
                success=True,
                message=f"User {target_user.username} {status_text} successfully"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user status: {str(e)}"
        )

@app.put("/api/admin/users/{user_id}", response_model=UserManagementResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_admin_or_higher)
):
    """Update user details"""
    try:
        with db_manager.get_session() as session:
            target_user = session.query(User).filter(User.id == user_id).first()

            if not target_user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )

            # Check permissions
            if not current_user.can_manage_user(target_user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to modify this user"
                )

            # Update password if provided
            if user_data.password:
                target_user.set_password(user_data.password)

            # Update role if provided and user has permission
            if user_data.role is not None:
                try:
                    role_enum = UserRole(user_data.role.upper())

                    # Validate role permissions
                    if current_user.role_enum == UserRole.ADMIN:
                        # Admins can only manage regular users
                        if role_enum != UserRole.USER:
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN,
                                detail="Admins can only manage regular users"
                            )
                    elif current_user.role_enum == UserRole.SUPER_ADMIN:
                        # Super admins can manage admin and user roles
                        if role_enum not in [UserRole.ADMIN, UserRole.USER]:
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN,
                                detail="Super admin can only create admin or user accounts"
                            )

                    target_user.role = role_enum.value
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid role. Valid roles: admin, user"
                    )

            # Update store access if provided
            if user_data.store_ids is not None:
                # Validate store access permissions
                if current_user.role_enum == UserRole.ADMIN:
                    admin_stores = current_user.get_store_ids()
                    invalid_stores = [store_id for store_id in user_data.store_ids if store_id not in admin_stores]
                    if invalid_stores:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"You don't have access to these stores: {', '.join(invalid_stores)}"
                        )

                target_user.set_store_ids(user_data.store_ids)

            # Update active status if provided
            if user_data.is_active is not None:
                target_user.is_active = user_data.is_active

            session.commit()
            session.refresh(target_user)

            return UserManagementResponse(
                success=True,
                message=f"User {target_user.username} updated successfully",
                user=UserResponse(
                    id=target_user.id,
                    username=target_user.username,
                    role=target_user.role_enum.value,
                    role_display=target_user.get_role_display(),
                    store_ids=target_user.get_store_ids(),
                    store_id=target_user.store_id,
                    created_by_id=None,
                    is_active=target_user.is_active,
                    created_at=target_user.created_at.isoformat(),
                    last_login=None
                )
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )

@app.get("/api/stores")
async def get_available_stores(current_user: User = Depends(get_current_user)):
    """Get all available store IDs based on user role"""
    try:
        with db_manager.get_session() as session:
            from database import VehicleProcessingRecord
            from sqlalchemy import distinct

            if current_user.role_enum == UserRole.SUPER_ADMIN:
                # Super admin can see all distinct environment_ids
                store_ids = session.query(distinct(VehicleProcessingRecord.environment_id)) \
                    .filter(VehicleProcessingRecord.environment_id.isnot(None)) \
                    .order_by(VehicleProcessingRecord.environment_id) \
                    .all()
                available_stores = [store_id[0] for store_id in store_ids if store_id[0]]
            else:
                # Admin or regular user sees only their assigned stores
                available_stores = current_user.get_store_ids()

            store_options = [
                {
                    "id": store_id,
                    "label": get_friendly_store_label(store_id)
                }
                for store_id in available_stores
            ]

            current_store_ids = current_user.get_store_ids()
            current_stores = [
                {
                    "id": store_id,
                    "label": get_friendly_store_label(store_id)
                }
                for store_id in current_store_ids
            ]

            return {
                "success": True,
                "stores": store_options,
                "role": current_user.role_enum.value,
                "current_store": current_stores
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching available stores: {str(e)}"
        )

@app.get("/api/debug/date-distribution")
async def get_date_distribution(
    store_id: Optional[str] = Query(None, description="Store ID for super admin filtering"),
    current_user: User = Depends(get_current_user)
):
    """Debug endpoint to check date distribution of vehicles"""
    try:
        with db_manager.get_session() as session:
            from database import VehicleProcessingRecord
            from sqlalchemy import func

            # Get date distribution
            query = session.query(
                func.date(VehicleProcessingRecord.processing_date).label('date'),
                func.count(VehicleProcessingRecord.id).label('count')
            )
            query = apply_store_filter(query, current_user, store_id)
            dates = query.group_by(
                func.date(VehicleProcessingRecord.processing_date)
            ).order_by(
                func.date(VehicleProcessingRecord.processing_date).desc()
            ).all()

            distribution = [
                {
                    "date": date.strftime('%Y-%m-%d'),
                    "count": count,
                    "day_name": date.strftime('%A')
                }
                for date, count in dates
            ]

            # Get min and max dates
            min_max_query = session.query(
                func.min(VehicleProcessingRecord.processing_date),
                func.max(VehicleProcessingRecord.processing_date)
            )
            min_max_query = apply_store_filter(min_max_query, current_user, store_id)
            min_max = min_max_query.first()

            return JSONResponse({
                "success": True,
                "date_distribution": distribution,
                "date_range": {
                    "min": min_max[0].strftime('%Y-%m-%d %H:%M:%S') if min_max[0] else None,
                    "max": min_max[1].strftime('%Y-%m-%d %H:%M:%S') if min_max[1] else None
                },
                "total_days": len(distribution),
                "current_month_count": len([d for d in distribution if d["date"].startswith(datetime.now().strftime('%Y-%m'))]),
                "current_year_count": len([d for d in distribution if d["date"].startswith(str(datetime.now().year))])
            })
    except Exception as e:
        print(f"Error getting date distribution: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    """User management page - requires admin authentication via JavaScript"""
    return templates.TemplateResponse("users.html", {"request": request})

@app.get("/cron", response_class=HTMLResponse)
async def cron_management_page(request: Request):
    """Cron management and onboarding page - requires super admin via JS"""
    return templates.TemplateResponse("cron_management.html", {"request": request})


@app.get("/dealerships/add", response_class=HTMLResponse)
async def add_dealership_page(request: Request):
    """Convenience route that opens the cron onboarding UI for adding dealerships."""
    return templates.TemplateResponse("cron_management.html", {"request": request, "view": "quick_onboard"})

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page - requires authentication via JavaScript"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request
    })

@app.get("/api/vehicles", response_model=VehiclesResponse)
async def get_vehicles(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str = Query("", description="Search by stock number"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    store_id: Optional[str] = Query(None, description="Store ID for super admin filtering"),
    current_user: User = Depends(get_current_user)
):
    """Get all vehicles with pagination and search"""
    print(f"Vehicles API called with start_date={start_date}, end_date={end_date}, search={search}")

    # Handle null/empty string dates
    if start_date == "null" or start_date == "":
        start_date = None
    if end_date == "null" or end_date == "":
        end_date = None

    try:
        search = search.strip()

        # Get vehicles from database
        with db_manager.get_session() as session:
            from database import VehicleProcessingRecord

            query = session.query(VehicleProcessingRecord)

            # Apply role-based store filtering
            print(f"DEBUG: User role={current_user.role}, store_ids={current_user.get_store_ids()}, selected_store_id={store_id}")
            query = apply_store_filter(query, current_user, store_id)
            print(f"DEBUG: Query after store filter applied")

            # Apply search filter if provided
            if search:
                query = query.filter(
                    VehicleProcessingRecord.stock_number.ilike(f'%{search}%')
                )

            # Apply date range filter if provided
            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    query = query.filter(VehicleProcessingRecord.processing_date >= start_dt)
                    print(f"Applied start date filter: {start_dt}")
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")

            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)  # Include entire end day
                    query = query.filter(VehicleProcessingRecord.processing_date < end_dt)
                    print(f"Applied end date filter: {end_dt}")
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")

            # Get total count
            total = query.count()
            print(f"DEBUG: Total vehicles after filtering: {total}")

            # Apply pagination and ordering
            vehicles = query.order_by(
                VehicleProcessingRecord.processing_date.desc()
            ).offset((page - 1) * per_page).limit(per_page).all()
            print(f"DEBUG: Returned {len(vehicles)} vehicles for page {page}")

            # Convert to response format
            vehicle_list = []
            for vehicle in vehicles:
                # Use actual vehicle name if available, otherwise create a friendly name
                display_name = vehicle.vehicle_name or f"Vehicle #{vehicle.stock_number}"
                if vehicle.vin and not vehicle.vehicle_name:
                    display_name += f" (VIN: ...{vehicle.vin[-6:]})"

                # Format processing date
                processing_date = vehicle.processing_date.strftime('%B %d, %Y at %I:%M %p') if vehicle.processing_date else 'Unknown'

                # Calculate status based on processing_status and success
                processing_status = getattr(vehicle, 'processing_status', None)
                # If processing_status is None, infer from processing_successful
                if processing_status is None:
                    processing_status = 'completed' if vehicle.processing_successful else 'failed'
                # Check for no build data first - this takes priority
                if getattr(vehicle, 'no_build_data_found', False):
                    status = '<i class="fas fa-clipboard-list"></i> No Build Data Found'
                    status_class = "warning"
                elif processing_status == 'processing':
                    status = '<i class="fas fa-spinner fa-spin"></i> Processing...'
                    status_class = "warning"
                elif processing_status == 'pending':
                    status = '<i class="fas fa-clock"></i> Pending'
                    status_class = "muted"
                elif vehicle.processing_successful:
                    status = '<i class="fas fa-check-circle"></i> Completed Successfully'
                    status_class = "success"
                else:
                    status = '<i class="fas fa-times-circle"></i> Processing Failed'
                    status_class = "danger"

                # Format features count
                features_text = f"{vehicle.marked_features_count or 0} features marked"

                # Format description status
                desc_status = '<i class="fas fa-edit"></i> Description Updated' if vehicle.description_updated else '<i class="fas fa-file-alt"></i> No Description'
                desc_class = "success" if vehicle.description_updated else "muted"

                # Format special features
                special_features = []
                if vehicle.no_fear_certificate:
                    special_features.append('<i class="fas fa-award"></i> NO FEAR Certified')

                # Book Values processing status
                book_values_status = '<i class="fas fa-chart-bar"></i> Book Values Processed' if vehicle.book_values_processed else '<i class="fas fa-chart-bar"></i> Book Values Pending'

                # Media Tab processing status
                media_status = '<i class="fas fa-images"></i> Media Processed' if vehicle.media_tab_processed else '<i class="fas fa-images"></i> Media Pending'

                # Overall processing completeness
                processing_steps = [
                    vehicle.processing_successful,
                    vehicle.description_updated,
                    vehicle.book_values_processed,
                    vehicle.media_tab_processed
                ]
                completed_steps = sum(processing_steps)
                total_steps = len(processing_steps)

                if completed_steps == total_steps:
                    processing_completeness = f'<i class="fas fa-check-circle"></i> Complete ({completed_steps}/{total_steps})'
                    processing_completeness_class = "success"
                elif completed_steps > total_steps // 2:
                    processing_completeness = f'<i class="fas fa-spinner"></i> Mostly Complete ({completed_steps}/{total_steps})'
                    processing_completeness_class = "warning"
                else:
                    processing_completeness = f'<i class="fas fa-exclamation-circle"></i> Partial ({completed_steps}/{total_steps})'
                    processing_completeness_class = "danger"

                vehicle_info = VehicleInfo(
                    id=vehicle.id,
                    name=display_name,
                    stock_number=vehicle.stock_number,
                    vehicle_name=vehicle.vehicle_name,
                    vin=vehicle.vin,
                    odometer=vehicle.odometer,
                    days_in_inventory=vehicle.days_in_inventory,
                    processing_date=processing_date,
                    processing_date_raw=vehicle.processing_date.isoformat() if vehicle.processing_date else None,
                    status=status,
                    status_class=status_class,
                    processing_status=processing_status,
                    processing_successful=vehicle.processing_successful,
                    description_status=desc_status,
                    description_class=desc_class,
                    description_updated=vehicle.description_updated,
                    features_count=vehicle.marked_features_count or 0,
                    features_text=features_text,
                    no_fear_certificate=vehicle.no_fear_certificate,
                    special_features=special_features,
                    processing_duration=vehicle.processing_duration,
                    has_errors=bool(vehicle.errors_encountered),
                    final_description=vehicle.final_description[:200] + '...' if vehicle.final_description and len(vehicle.final_description) > 200 else vehicle.final_description,
                    no_build_data_found=getattr(vehicle, 'no_build_data_found', False),
                    book_values_processed=vehicle.book_values_processed,
                    media_tab_processed=vehicle.media_tab_processed,
                    book_values_status=book_values_status,
                    media_status=media_status,
                    processing_completeness=processing_completeness,
                    processing_completeness_class=processing_completeness_class
                )
                vehicle_list.append(vehicle_info)

            pagination = PaginationInfo(
                page=page,
                per_page=per_page,
                total=total,
                pages=(total + per_page - 1) // per_page,
                has_prev=page > 1,
                has_next=page * per_page < total
            )

            return VehiclesResponse(
                success=True,
                vehicles=vehicle_list,
                pagination=pagination
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/vehicle/{vehicle_id}", response_model=VehicleDetailResponse)
async def get_vehicle_details(
    vehicle_id: int,
    store_id: Optional[str] = Query(None, description="Store ID for super admin filtering"),
    current_user: User = Depends(get_current_user)
):
    """Get detailed information for a specific vehicle"""
    try:
        with db_manager.get_session() as session:
            from database import VehicleProcessingRecord

            query = session.query(VehicleProcessingRecord).filter(VehicleProcessingRecord.id == vehicle_id)
            query = apply_store_filter(query, current_user, store_id)
            vehicle = query.first()

            if not vehicle:
                raise HTTPException(status_code=404, detail="Vehicle not found")

            # Parse JSON fields safely
            import json
            starred_features = []
            starred_features_summary = None
            if vehicle.starred_features:
                try:
                    starred_features = json.loads(vehicle.starred_features)
                    if starred_features:
                        feature_names = []
                        for feature in starred_features:
                            if isinstance(feature, dict) and 'text' in feature:
                                feature_names.append(feature['text'][:50])  # Truncate long feature names
                            elif isinstance(feature, str):
                                feature_names.append(feature[:50])
                        starred_features_summary = ", ".join(feature_names[:5])  # Show first 5 features
                        if len(feature_names) > 5:
                            starred_features_summary += f" (+{len(feature_names)-5} more)"
                except:
                    pass

            feature_decisions = {}
            feature_decisions_summary = None
            if vehicle.feature_decisions:
                try:
                    feature_decisions = json.loads(vehicle.feature_decisions)
                    if feature_decisions and isinstance(feature_decisions, dict):
                        # Create a summary of AI decisions
                        decision_count = len(feature_decisions)
                        feature_decisions_summary = f"AI analyzed {decision_count} features with recommendations"
                except:
                    pass

            errors_encountered = []
            if vehicle.errors_encountered:
                try:
                    errors_encountered = json.loads(vehicle.errors_encountered)
                except:
                    pass

            media_totals_found = {}
            if vehicle.media_totals_found:
                try:
                    media_totals_found = json.loads(vehicle.media_totals_found)
                except:
                    pass

            # Parse book values
            book_values_before = {}
            if vehicle.book_values_before_processing:
                try:
                    book_values_before = json.loads(vehicle.book_values_before_processing)
                except:
                    pass

            book_values_after = {}
            if vehicle.book_values_after_processing:
                try:
                    book_values_after = json.loads(vehicle.book_values_after_processing)
                except:
                    pass

            ai_analysis_result = {}
            if vehicle.ai_analysis_result:
                try:
                    ai_analysis_result = json.loads(vehicle.ai_analysis_result)
                except:
                    pass

            vehicle_detail = VehicleDetail(
                id=vehicle.id,
                stock_number=vehicle.stock_number,
                vehicle_name=vehicle.vehicle_name,
                vin=vehicle.vin,
                odometer=vehicle.odometer,
                days_in_inventory=vehicle.days_in_inventory,
                processing_date=vehicle.processing_date.strftime('%B %d, %Y at %I:%M %p') if vehicle.processing_date else None,
                processing_status=getattr(vehicle, 'processing_status', None) or ('completed' if vehicle.processing_successful else 'failed'),
                processing_successful=vehicle.processing_successful,
                processing_duration=vehicle.processing_duration,
                original_description=vehicle.original_description,
                ai_generated_description=vehicle.ai_generated_description,
                final_description=vehicle.final_description,
                description_updated=vehicle.description_updated,
                starred_features=starred_features,
                starred_features_summary=starred_features_summary,
                marked_features_count=vehicle.marked_features_count or 0,
                feature_decisions=feature_decisions,
                feature_decisions_summary=feature_decisions_summary,
                no_fear_certificate=vehicle.no_fear_certificate,
                no_fear_certificate_text=vehicle.no_fear_certificate_text,
                book_values_processed=vehicle.book_values_processed,
                book_values_before_processing=book_values_before,
                book_values_after_processing=book_values_after,
                media_tab_processed=vehicle.media_tab_processed,
                media_totals_found=media_totals_found,
                ai_analysis_result=ai_analysis_result,
                errors_encountered=errors_encountered,
                screenshot_path=vehicle.screenshot_path,
                no_build_data_found=getattr(vehicle, 'no_build_data_found', False)
            )

            return VehicleDetailResponse(
                success=True,
                vehicle=vehicle_detail
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/vehicle/{vehicle_id}")
async def delete_vehicle(vehicle_id: int, current_user: User = Depends(get_current_user)):
    """Delete a vehicle record"""
    try:
        with db_manager.get_session() as session:
            from database import VehicleProcessingRecord

            # Find the vehicle record
            vehicle = session.query(VehicleProcessingRecord).filter(
                VehicleProcessingRecord.id == vehicle_id,
                VehicleProcessingRecord.environment_id == current_user.store_id
            ).first()

            if not vehicle:
                raise HTTPException(status_code=404, detail="Vehicle not found")

            # Store vehicle info for response
            vehicle_info = {
                "stock_number": vehicle.stock_number,
                "vehicle_name": vehicle.vehicle_name
            }

            # Delete the vehicle record
            session.delete(vehicle)
            session.commit()

            return {
                "success": True,
                "message": f"Vehicle {vehicle_info['stock_number']} deleted successfully",
                "deleted_vehicle": vehicle_info
            }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete vehicle: {str(e)}")

@app.get("/api/statistics", response_model=StatisticsResponse)
async def get_statistics(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    store_id: Optional[str] = Query(None, description="Store ID for super admin filtering"),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard statistics"""
    print(f"Statistics API called with start_date={start_date}, end_date={end_date}, store_id={store_id}")

    # Handle null/empty string dates
    if start_date == "null" or start_date == "":
        start_date = None
    if end_date == "null" or end_date == "":
        end_date = None

    try:
        with db_manager.get_session() as session:
            from database import VehicleProcessingRecord

            # Base query with store filtering
            base_query = session.query(VehicleProcessingRecord)
            base_query = apply_store_filter(base_query, current_user, store_id)

            # Apply date range filter if provided
            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    base_query = base_query.filter(VehicleProcessingRecord.processing_date >= start_dt)
                    print(f"Statistics: Applied start date filter: {start_dt}")
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")

            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)  # Include entire end day
                    base_query = base_query.filter(VehicleProcessingRecord.processing_date < end_dt)
                    print(f"Statistics: Applied end date filter: {end_dt}")
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")

            # Basic counts
            total_vehicles = base_query.count()
            successful_processing = base_query.filter_by(processing_successful=True).count()
            with_descriptions = base_query.filter_by(description_updated=True).count()
            with_no_fear = base_query.filter_by(no_fear_certificate=True).count()

            # Calculate success rate
            success_rate = (successful_processing / total_vehicles * 100) if total_vehicles > 0 else 0

            # Recent activity (last 7 days)
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            recent_vehicles = base_query.filter(
                VehicleProcessingRecord.processing_date >= seven_days_ago
            ).count()

            # Total features marked
            total_features = base_query.filter(
                VehicleProcessingRecord.marked_features_count.isnot(None)
            ).with_entities(VehicleProcessingRecord.marked_features_count).all()

            total_features_marked = sum(count[0] or 0 for count in total_features)
            avg_features_per_vehicle = (total_features_marked / total_vehicles) if total_vehicles > 0 else 0

            # Calculate book value totals using the selected date range (or MTD/YTD if no range selected)
            # If user selected a date range, use that for book values
            # Otherwise fall back to MTD/YTD
            print(f"DEBUG BOOK VALUE QUERY: start_date={start_date}, end_date={end_date}, type(start_date)={type(start_date)}")
            if start_date and end_date:
                # Use the selected date range for both MTD and YTD (they'll be the same)
                # Note: base_query already has the date filter applied above
                print(f"DEBUG: Using selected date range for book values: {start_date} to {end_date}")
                mtd_vehicles = base_query.filter(
                    VehicleProcessingRecord.book_values_processed == True,
                    VehicleProcessingRecord.book_values_before_processing.isnot(None),
                    VehicleProcessingRecord.book_values_after_processing.isnot(None)
                ).all()
                print(f"DEBUG: Found {len(mtd_vehicles)} vehicles with book values in selected range")
                ytd_vehicles = mtd_vehicles  # Same as MTD when date range is selected
            else:
                # No date range selected - use MTD/YTD
                month_start = get_month_start()
                year_start = get_year_start()

                # Get vehicles with book values for MTD
                mtd_vehicles = base_query.filter(
                    VehicleProcessingRecord.processing_date >= month_start,
                    VehicleProcessingRecord.book_values_processed == True,
                    VehicleProcessingRecord.book_values_before_processing.isnot(None),
                    VehicleProcessingRecord.book_values_after_processing.isnot(None)
                ).all()

                # Get vehicles with book values for YTD
                ytd_vehicles = base_query.filter(
                    VehicleProcessingRecord.processing_date >= year_start,
                    VehicleProcessingRecord.book_values_processed == True,
                    VehicleProcessingRecord.book_values_before_processing.isnot(None),
                    VehicleProcessingRecord.book_values_after_processing.isnot(None)
                ).all()

            # Calculate total book value differences and insights using the refined aggregator
            total_book_value_mtd, mtd_insights = aggregate_book_value_insights_for_period(mtd_vehicles)
            total_book_value_ytd, ytd_insights = aggregate_book_value_insights_for_period(ytd_vehicles)

            # Calculate time saved (based on total successful vehicles)
            time_saved_minutes, time_saved_formatted = calculate_time_saved(successful_processing)

            statistics = Statistics(
                total_vehicles=total_vehicles,
                successful_processing=successful_processing,
                success_rate=f"{success_rate:.1f}%",
                success_rate_value=success_rate,
                descriptions_updated=with_descriptions,
                no_fear_certificates=with_no_fear,
                recent_activity_7_days=recent_vehicles,
                total_features_marked=total_features_marked,
                avg_features_per_vehicle=f"{avg_features_per_vehicle:.1f}",
                total_book_value_mtd=total_book_value_mtd,
                total_book_value_ytd=total_book_value_ytd,
                book_value_insights_mtd=mtd_insights,
                book_value_insights_ytd=ytd_insights,
                time_saved_minutes=time_saved_minutes,
                time_saved_formatted=time_saved_formatted
            )

            return StatisticsResponse(
                success=True,
                statistics=statistics
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/debug/book-values")
async def debug_book_values(
    store_id: Optional[str] = Query(None, description="Store ID for super admin filtering"),
    current_user: User = Depends(get_current_user)
):
    """Debug endpoint to inspect book values data structure"""
    try:
        with db_manager.get_session() as session:
            from database import VehicleProcessingRecord

            # Get a few records with book values
            query = session.query(VehicleProcessingRecord)
            query = apply_store_filter(query, current_user, store_id)
            vehicles_with_book_values = query.filter(
                VehicleProcessingRecord.book_values_processed == True,
                VehicleProcessingRecord.book_values_before_processing.isnot(None)
            ).limit(5).all()

            debug_data = []
            for vehicle in vehicles_with_book_values:
                try:
                    before_data = json.loads(vehicle.book_values_before_processing) if vehicle.book_values_before_processing else {}
                    after_data = json.loads(vehicle.book_values_after_processing) if vehicle.book_values_after_processing else {}
                    difference = calculate_book_value_difference(before_data, after_data)

                    debug_data.append({
                        "stock_number": vehicle.stock_number,
                        "before_data": before_data,
                        "after_data": after_data,
                        "calculated_difference": difference
                    })
                except Exception as e:
                    debug_data.append({
                        "stock_number": vehicle.stock_number,
                        "error": str(e),
                        "before_raw": vehicle.book_values_before_processing,
                        "after_raw": vehicle.book_values_after_processing
                    })

            return {
                "success": True,
                "total_vehicles_with_book_values": len(vehicles_with_book_values),
                "sample_data": debug_data
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/recent-activity", response_model=ActivityResponse)
async def get_recent_activity(
    limit: int = Query(10, ge=1, le=50),
    store_id: Optional[str] = Query(None, description="Store ID for super admin filtering"),
    current_user: User = Depends(get_current_user)
):
    """Get recent processing activity"""
    try:
        with db_manager.get_session() as session:
            from database import VehicleProcessingRecord

            query = session.query(VehicleProcessingRecord)
            query = apply_store_filter(query, current_user, store_id)

            recent_vehicles = query.order_by(
                VehicleProcessingRecord.processing_date.desc()
            ).limit(limit).all()

            activity = []
            for vehicle in recent_vehicles:
                # Time ago calculation
                if vehicle.processing_date:
                    time_diff = datetime.utcnow() - vehicle.processing_date
                    if time_diff.days > 0:
                        time_ago = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
                    elif time_diff.seconds > 3600:
                        hours = time_diff.seconds // 3600
                        time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
                    elif time_diff.seconds > 60:
                        minutes = time_diff.seconds // 60
                        time_ago = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
                    else:
                        time_ago = "Just now"
                else:
                    time_ago = "Unknown time"

                # Activity description
                action_parts = []
                if vehicle.processing_successful:
                    action_parts.append("✅ processed")
                else:
                    action_parts.append("❌ failed to process")

                if vehicle.description_updated:
                    action_parts.append("📝 updated description")

                if vehicle.marked_features_count and vehicle.marked_features_count > 0:
                    action_parts.append(f"⭐ marked {vehicle.marked_features_count} features")

                if vehicle.no_fear_certificate:
                    action_parts.append("🏆 NO FEAR certified")

                action_description = f"Vehicle #{vehicle.stock_number} " + ", ".join(action_parts)

                activity_item = ActivityItem(
                    id=vehicle.id,
                    stock_number=vehicle.stock_number,
                    action=action_description,
                    time_ago=time_ago,
                    processing_successful=vehicle.processing_successful,
                    processing_date=vehicle.processing_date.isoformat() if vehicle.processing_date else None
                )
                activity.append(activity_item)

            return ActivityResponse(
                success=True,
                activity=activity
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={"success": False, "error": "Endpoint not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error"}
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == '__main__':
    print(f"🚀 Starting Dealership Dashboard at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("📊 Dashboard will be available at: http://localhost:9000")
    print("📖 API Documentation at: http://localhost:9000/api/docs")
    print("🔍 Search vehicles by stock number")
    print("📈 View processing statistics and recent activity")
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=9000,
        reload=True,
        log_level="info"
    )
