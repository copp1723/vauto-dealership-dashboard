#!/usr/bin/env python3
"""
Password Reset Utility for Dealership Dashboard
Allows resetting passwords for existing users.
"""

import os
import sys
from getpass import getpass
from database import get_database_manager, User

def list_users():
    """List all users in the database"""
    print("=== Current Users ===")
    db_manager = get_database_manager()
    
    with db_manager.get_session() as session:
        users = session.query(User).all()
        
        if not users:
            print("No users found in database.")
            return []
        
        print(f"{'ID':<5} {'Username':<20} {'Role':<15} {'Active':<8} {'Store IDs'}")
        print("-" * 70)
        
        for user in users:
            store_ids = ', '.join(user.get_store_ids()) if user.get_store_ids() else 'All'
            active_status = "Yes" if user.is_active else "No"
            print(f"{user.id:<5} {user.username:<20} {user.role:<15} {active_status:<8} {store_ids}")
        
        return users

def reset_user_password(username, new_password):
    """Reset password for a specific user"""
    db_manager = get_database_manager()
    
    with db_manager.get_session() as session:
        user = session.query(User).filter(User.username == username).first()
        
        if not user:
            print(f"❌ User '{username}' not found.")
            return False
        
        # Set new password
        user.set_password(new_password)
        session.commit()
        
        print(f"✅ Password reset successfully for user: {username}")
        print(f"   Role: {user.get_role_display()}")
        print(f"   Active: {'Yes' if user.is_active else 'No'}")
        return True

def main():
    """Main password reset function"""
    print("=== Password Reset Utility ===")
    print()
    
    try:
        # Initialize database
        print("🔧 Connecting to database...")
        db_manager = get_database_manager()
        print("✅ Database connection established")
        print()
        
        # List current users
        users = list_users()
        if not users:
            return
        
        print()
        
        # Get username to reset
        username = input("Enter username to reset password for: ").strip()
        if not username:
            print("❌ Username cannot be empty")
            return
        
        # Get new password
        while True:
            new_password = getpass("Enter new password: ").strip()
            if len(new_password) < 6:
                print("❌ Password must be at least 6 characters long")
                continue
            
            confirm_password = getpass("Confirm new password: ").strip()
            if new_password != confirm_password:
                print("❌ Passwords don't match")
                continue
            break
        
        # Confirm reset
        print(f"\n⚠️  You are about to reset the password for user: {username}")
        confirm = input("Are you sure? (yes/no): ").lower().strip()
        
        if confirm not in ['yes', 'y']:
            print("❌ Password reset cancelled")
            return
        
        # Reset password
        print("\n🔐 Resetting password...")
        if reset_user_password(username, new_password):
            print("\n✅ Password reset completed successfully!")
            print(f"User '{username}' can now login with the new password.")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Password reset cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during password reset: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
