"""
Create default admin user for KNOWA AI
Usage: python create_admin.py
"""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).resolve().parent / ".env")

from app.db.database import SessionLocal
from app.db.models import User, Tenant
from app.auth.security import hash_password


def create_default_admin():
    """Create default admin user if it doesn't exist."""
    db = SessionLocal()
    try:
        # Check if admin user already exists
        existing_user = db.query(User).filter(User.email == "admin@gmail.com").first()
        if existing_user:
            print("Admin user already exists: admin@gmail.com")
            return

        # Create default tenant
        tenant = Tenant(
            name="KNOWA AI",
            slug="knowa-ai",
            plan="free"
        )
        db.add(tenant)
        db.flush()

        # Create admin user
        admin_user = User(
            tenant_id=tenant.id,
            email="admin@gmail.com",
            hashed_password=hash_password("Admin@123"),
            full_name="Admin User",
            role="admin",
            is_active=True
        )
        db.add(admin_user)
        db.commit()

        print("Default admin user created successfully!")
        print("Email: admin@gmail.com")
        print("Password: Admin@123")
        print("Role: admin")

    except Exception as e:
        print(f"Error creating admin user: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    create_default_admin()