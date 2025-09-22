#!/usr/bin/env python3
"""
Dealership Dashboard Startup Script
Easy way to start the professional vehicle processing dashboard
"""

import os
import sys
import subprocess

def check_requirements():
    """Check if required packages are installed"""
    try:
        import fastapi
        import uvicorn
        import jinja2
        import aiofiles
        import sqlalchemy
        print("✅ All required packages are available")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e.name}")
        print("📦 Installing requirements...")
        
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
            print("✅ Requirements installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install requirements")
            print("Please run: pip install -r requirements.txt")
            return False

def main():
    print("🚗 Dealership Dashboard Startup")
    print("="*50)
    
    # Check if we're in the right directory
    if not os.path.exists('app.py'):
        print("❌ Please run this script from the dealership_dashboard directory")
        return
    
    # Check requirements
    if not check_requirements():
        return
    
    # Check PostgreSQL database configuration
    print("📊 Checking PostgreSQL database configuration...")
    try:
        # Add parent directory to path
        sys.path.append('..')
        from database import get_database_manager
        db_manager = get_database_manager()
        print(f"   Database URL: {db_manager.db_url}")
        print("   PostgreSQL connection: OK")
    except Exception as e:
        print(f"   Error: PostgreSQL connection failed: {e}")
        print("   Please ensure PostgreSQL is running and credentials are set in .env file")
        return
    
    print("\n🚀 Starting FastAPI dashboard server...")
    print("📱 Dashboard URL: http://localhost:9000")
    print("📖 API Documentation: http://localhost:9000/api/docs")
    print("📚 ReDoc Documentation: http://localhost:9000/api/redoc")
    print("🔍 Features:")
    print("   • Modern FastAPI backend with automatic API docs")
    print("   • Search vehicles by stock number")
    print("   • View processing statistics")
    print("   • Filter by status and description updates")
    print("   • Detailed vehicle information modals")
    print("   • Recent activity feed")
    print("   • Responsive design for mobile devices")
    print("   • Type-safe API with Pydantic models")
    print("\n💡 Tip: Press Ctrl+C to stop the server")
    print("="*50)
    
    # Start the FastAPI app
    try:
        import uvicorn
        uvicorn.run(
            "app:app", 
            host="0.0.0.0", 
            port=9000, 
            reload=False,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n👋 FastAPI dashboard server stopped")
    except Exception as e:
        print(f"\n❌ Error starting dashboard: {e}")
        print("Please check the error message above and try again")

if __name__ == '__main__':
    main()