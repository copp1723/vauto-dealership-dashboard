#!/usr/bin/env python3
"""
Setup Script for Dealership Dashboard
Creates the initial super admin user and sets up the role-based system.
"""

import os
import sys
from getpass import getpass
from database import get_database_manager, create_super_admin, migrate_users_to_role_system

def main():
    """Main setup function"""
    print("=== Dealership Dashboard Setup ===")
    print("This script will set up the role-based user system and create a super admin user.")
    print()
    
    try:
        # Initialize database manager
        print("🔧 Initializing database connection...")
        db_manager = get_database_manager()
        print("✅ Database connection established")
        
        # Run migration
        print("\n🔄 Running user migration...")
        migrate_users_to_role_system(db_manager)
        print("✅ Migration completed")
        
        # Check if super admin already exists
        with db_manager.get_session() as session:
            from database import User, UserRole
            existing_super_admin = session.query(User).filter(User.role == UserRole.SUPER_ADMIN).first()
            
            if existing_super_admin:
                print(f"\n⚠️  Super admin already exists: {existing_super_admin.username}")
                response = input("Do you want to create another super admin? (y/n): ").lower().strip()
                if response != 'y':
                    print("Setup complete. Existing super admin:")
                    print(f"   Username: {existing_super_admin.username}")
                    return
        
        # Get super admin credentials
        print("\n👤 Creating Super Admin User")
        print("The super admin can access all stores and manage all users.")
        print()
        
        username = input("Enter super admin username [superadmin]: ").strip()
        if not username:
            username = "superadmin"
        
        while True:
            password = getpass("Enter super admin password: ").strip()
            if len(password) < 6:
                print("❌ Password must be at least 6 characters long")
                continue
            
            confirm_password = getpass("Confirm password: ").strip()
            if password != confirm_password:
                print("❌ Passwords don't match")
                continue
            break
        
        # Create super admin
        print("\n🔐 Creating super admin...")
        super_admin = create_super_admin(db_manager, username, password)
        
        print("\n✅ Setup completed successfully!")
        print()
        print("=== Login Information ===")
        print(f"Username: {username}")
        print(f"Role: Super Administrator")
        print("Access: All stores")
        print()
        print("🌐 You can now login to the dashboard at: http://localhost:8000")
        print()
        print("📝 Next steps:")
        print("1. Login with your super admin credentials")
        print("2. Use the 'Manage Users' button to create admin users")
        print("3. Admin users can then create regular users")
        print()
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during setup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()