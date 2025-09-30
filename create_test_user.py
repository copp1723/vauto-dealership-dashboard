#!/usr/bin/env python3
"""Quick script to create a test user"""

from database import get_database_manager, User, UserRole

def create_test_user():
    db_manager = get_database_manager()

    with db_manager.get_session() as session:
        # Check if test user exists
        existing = session.query(User).filter(User.username == "testuser").first()
        if existing:
            print("Test user already exists")
            return

        # Create test user
        test_user = User(
            username="testuser",
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )
        test_user.set_password("testpass123")

        session.add(test_user)
        session.commit()

        print("Test user created: testuser / testpass123")

if __name__ == "__main__":
    create_test_user()