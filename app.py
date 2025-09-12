#!/usr/bin/env python3
"""
Dealership Dashboard - FastAPI Backend
Professional dashboard for vehicle processing database
"""

import os
import sys
import hashlib
import json
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
from passlib.context import CryptContext

load_dotenv()

from database import get_database_manager, User

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
    store_id: str = Field(..., min_length=1, max_length=100)

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: int
    username: str
    store_id: str
    created_at: str
    last_login: Optional[str] = None

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

# Initialize database manager (will use environment variables for database connection)
print("Initializing database connection...")
db_manager = get_database_manager()
if SECRET_KEY.startswith("your-secret-key-change-in-production"):
    print("⚠️ WARNING: Using default SECRET_KEY. Set SECRET_KEY in your .env so JWT tokens remain valid across restarts.")

# Authentication Helper Functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a plain password"""
    return pwd_context.hash(password)

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
        if user is None:
            raise credentials_exception
        return user

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
        'best_improvement': {'category': '', 'amount': 0.0},
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
            difference = after_val - before_val
            
            insights['categories'][category] = {
                'before': before_val,
                'after': after_val,
                'difference': difference,
                'improvement': difference > 0
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
        insights['best_improvement'] = {'category': best_category, 'amount': best_improvement}
        
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

def calculate_time_saved(vehicle_count: int) -> tuple[int, str]:
    """Calculate time saved based on vehicle count (11 minutes per vehicle)"""
    total_minutes = vehicle_count * 11
    hours = total_minutes // 60
    minutes = total_minutes % 60
    
    if hours > 0:
        formatted = f"{hours} HOUR{'S' if hours != 1 else ''} {minutes} MINUTE{'S' if minutes != 1 else ''}"
    else:
        formatted = f"{minutes} MINUTE{'S' if minutes != 1 else ''}"
    
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
@app.post("/api/signup", response_model=UserResponse)
async def signup(user_data: UserCreate):
    """User registration endpoint"""
    try:
        with db_manager.get_session() as session:
            # Check if username already exists
            existing_user = session.query(User).filter(User.username == user_data.username).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already registered"
                )
            
            # Create new user
            new_user = User(
                username=user_data.username,
                store_id=user_data.store_id
            )
            new_user.set_password(user_data.password)
            
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            
            return UserResponse(
                id=new_user.id,
                username=new_user.username,
                store_id=new_user.store_id,
                created_at=new_user.created_at.isoformat(),
                last_login=new_user.last_login.isoformat() if new_user.last_login else None
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )

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
        
        # Update last login
        with db_manager.get_session() as session:
            session.query(User).filter(User.id == user.id).update({
                "last_login": datetime.utcnow()
            })
            session.commit()
        
        # Create proper JWT access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username}, expires_delta=access_token_expires
        )
        
        return Token(access_token=access_token, token_type="bearer")
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
        store_id=current_user.store_id,
        created_at=current_user.created_at.isoformat(),
        last_login=current_user.last_login.isoformat() if current_user.last_login else None
    )

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    """Signup page"""
    return templates.TemplateResponse("signup.html", {"request": request})

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
    current_user: User = Depends(get_current_user)
):
    """Get all vehicles with pagination and search"""
    try:
        search = search.strip()
        
        # Get vehicles from database
        with db_manager.get_session() as session:
            from database import VehicleProcessingRecord
            
            query = session.query(VehicleProcessingRecord)
            
            # Filter by user's store_id (environment_id)
            query = query.filter(VehicleProcessingRecord.environment_id == current_user.store_id)
            
            # Apply search filter if provided
            if search:
                query = query.filter(
                    VehicleProcessingRecord.stock_number.ilike(f'%{search}%')
                )
            
            # Get total count
            total = query.count()
            
            # Apply pagination and ordering
            vehicles = query.order_by(
                VehicleProcessingRecord.processing_date.desc()
            ).offset((page - 1) * per_page).limit(per_page).all()
            
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
                    status = "📋 No Build Data Found"
                    status_class = "warning"
                elif processing_status == 'processing':
                    status = "🔄 Processing..."
                    status_class = "warning"
                elif processing_status == 'pending':
                    status = "⏳ Pending"
                    status_class = "muted"
                elif vehicle.processing_successful:
                    status = "✅ Completed Successfully"
                    status_class = "success"
                else:
                    status = "❌ Processing Failed"
                    status_class = "danger"
                
                # Format features count
                features_text = f"{vehicle.marked_features_count or 0} features marked"
                
                # Format description status
                desc_status = "📝 Description Updated" if vehicle.description_updated else "📄 No Description"
                desc_class = "success" if vehicle.description_updated else "muted"
                
                # Format special features
                special_features = []
                if vehicle.no_fear_certificate:
                    special_features.append("🏆 NO FEAR Certified")
                
                # Book Values processing status
                book_values_status = "📊 Book Values Processed" if vehicle.book_values_processed else "📊 Book Values Pending"
                
                # Media Tab processing status
                media_status = "📸 Media Processed" if vehicle.media_tab_processed else "📸 Media Pending"
                
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
                    processing_completeness = f"✅ Complete ({completed_steps}/{total_steps})"
                    processing_completeness_class = "success"
                elif completed_steps > total_steps // 2:
                    processing_completeness = f"🔄 Mostly Complete ({completed_steps}/{total_steps})"
                    processing_completeness_class = "warning"
                else:
                    processing_completeness = f"🟡 Partial ({completed_steps}/{total_steps})"
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
async def get_vehicle_details(vehicle_id: int, current_user: User = Depends(get_current_user)):
    """Get detailed information for a specific vehicle"""
    try:
        with db_manager.get_session() as session:
            from database import VehicleProcessingRecord
            
            vehicle = session.query(VehicleProcessingRecord).filter(
                VehicleProcessingRecord.id == vehicle_id,
                VehicleProcessingRecord.environment_id == current_user.store_id
            ).first()
            
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
async def get_statistics(current_user: User = Depends(get_current_user)):
    """Get dashboard statistics"""
    try:
        with db_manager.get_session() as session:
            from database import VehicleProcessingRecord
            
            # Base query filtered by user's store_id
            base_query = session.query(VehicleProcessingRecord).filter(
                VehicleProcessingRecord.environment_id == current_user.store_id
            )
            
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
            
            # Calculate book value totals (Month-to-Date and Year-to-Date)
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
            
            # Calculate total book value differences and insights
            total_book_value_mtd = 0.0
            mtd_insights = {'categories': {}, 'total_difference': 0.0, 'best_improvement': {'category': '', 'amount': 0.0}, 'primary_source': 'KBB', 'summary': 'No MTD data available'}
            
            for vehicle in mtd_vehicles:
                try:
                    before_data = json.loads(vehicle.book_values_before_processing) if vehicle.book_values_before_processing else {}
                    after_data = json.loads(vehicle.book_values_after_processing) if vehicle.book_values_after_processing else {}
                    
                    # Calculate vehicle insights
                    vehicle_insights = calculate_book_value_insights(before_data, after_data)
                    difference = calculate_book_value_difference(before_data, after_data)
                    total_book_value_mtd += difference
                    
                    # Aggregate insights
                    for category, data in vehicle_insights['categories'].items():
                        if category not in mtd_insights['categories']:
                            mtd_insights['categories'][category] = {'before': 0, 'after': 0, 'difference': 0, 'improvement': False}
                        mtd_insights['categories'][category]['difference'] += data['difference']
                        
                except (json.JSONDecodeError, TypeError):
                    continue
            
            # Update MTD summary
            mtd_insights['total_difference'] = total_book_value_mtd
            if total_book_value_mtd > 0:
                mtd_insights['summary'] = f"${total_book_value_mtd:,.0f} total increase (MTD)"
            elif total_book_value_mtd < 0:
                mtd_insights['summary'] = f"${abs(total_book_value_mtd):,.0f} total decrease (MTD)"
            else:
                mtd_insights['summary'] = "No MTD value changes detected"
            
            total_book_value_ytd = 0.0
            ytd_insights = {'categories': {}, 'total_difference': 0.0, 'best_improvement': {'category': '', 'amount': 0.0}, 'primary_source': 'KBB', 'summary': 'No YTD data available'}
            
            for vehicle in ytd_vehicles:
                try:
                    before_data = json.loads(vehicle.book_values_before_processing) if vehicle.book_values_before_processing else {}
                    after_data = json.loads(vehicle.book_values_after_processing) if vehicle.book_values_after_processing else {}
                    
                    # Calculate vehicle insights
                    vehicle_insights = calculate_book_value_insights(before_data, after_data)
                    difference = calculate_book_value_difference(before_data, after_data)
                    total_book_value_ytd += difference
                    
                    # Aggregate insights
                    for category, data in vehicle_insights['categories'].items():
                        if category not in ytd_insights['categories']:
                            ytd_insights['categories'][category] = {'before': 0, 'after': 0, 'difference': 0, 'improvement': False}
                        ytd_insights['categories'][category]['difference'] += data['difference']
                        
                except (json.JSONDecodeError, TypeError):
                    continue
            
            # Update YTD summary
            ytd_insights['total_difference'] = total_book_value_ytd
            if total_book_value_ytd > 0:
                ytd_insights['summary'] = f"${total_book_value_ytd:,.0f} total increase (YTD)"
            elif total_book_value_ytd < 0:
                ytd_insights['summary'] = f"${abs(total_book_value_ytd):,.0f} total decrease (YTD)"
            else:
                ytd_insights['summary'] = "No YTD value changes detected"
            
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
async def debug_book_values(current_user: User = Depends(get_current_user)):
    """Debug endpoint to inspect book values data structure"""
    try:
        with db_manager.get_session() as session:
            from database import VehicleProcessingRecord
            
            # Get a few records with book values
            vehicles_with_book_values = session.query(VehicleProcessingRecord).filter(
                VehicleProcessingRecord.environment_id == current_user.store_id,
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
    current_user: User = Depends(get_current_user)
):
    """Get recent processing activity"""
    try:
        with db_manager.get_session() as session:
            from database import VehicleProcessingRecord
            
            recent_vehicles = session.query(VehicleProcessingRecord).filter(
                VehicleProcessingRecord.environment_id == current_user.store_id
            ).order_by(
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