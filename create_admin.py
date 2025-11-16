#!/usr/bin/env python3
"""
Create an admin user for the CMMC platform
"""
import asyncio
import asyncpg
import os
import sys
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def create_admin_user():
    """Create an admin user with full access"""

    # Load required settings from environment to avoid hardcoding secrets
    db_host = os.getenv("CMMC_DB_HOST", "localhost")
    db_port = int(os.getenv("CMMC_DB_PORT", "5432"))
    db_user = os.getenv("CMMC_DB_USER")
    db_password = os.getenv("CMMC_DB_PASSWORD")
    db_name = os.getenv("CMMC_DB_NAME", "cmmc_platform")

    admin_email = os.getenv("CMMC_ADMIN_EMAIL")
    admin_password = os.getenv("CMMC_ADMIN_PASSWORD")
    admin_full_name = os.getenv("CMMC_ADMIN_NAME", "Admin User")

    missing_vars = [
        name for name, val in [
            ("CMMC_DB_USER", db_user),
            ("CMMC_DB_PASSWORD", db_password),
            ("CMMC_ADMIN_EMAIL", admin_email),
            ("CMMC_ADMIN_PASSWORD", admin_password),
        ] if not val
    ]
    if missing_vars:
        raise ValueError(f"Missing required environment vars: {', '.join(missing_vars)}")

    # Database connection
    conn = await asyncpg.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database=db_name,
    )

    try:
        # User details
        email = admin_email
        password = admin_password
        full_name = admin_full_name

        # Hash the password
        password_hash = pwd_context.hash(password)

        # Check if user already exists
        existing = await conn.fetchval(
            "SELECT id FROM users WHERE email = $1",
            email.lower()
        )

        if existing:
            print(f"User {email} already exists. Updating password and role...")

            # Update existing user
            await conn.execute(
                """
                UPDATE users
                SET password_hash = $1, role = 'admin', active = TRUE
                WHERE email = $2
                """,
                password_hash,
                email.lower()
            )

            user_id = existing
            print(f"✓ User {email} updated successfully!")

        else:
            print(f"Creating new admin user: {email}")

            # First, create an organization for the user
            org_id = await conn.fetchval(
                """
                INSERT INTO organizations (name, active)
                VALUES ($1, TRUE)
                RETURNING id
                """,
                "SmartGnosis Admin"
            )

            # Create the admin user
            user_id = await conn.fetchval(
                """
                INSERT INTO users (email, password_hash, full_name, organization_id, role, active)
                VALUES ($1, $2, $3, $4, 'admin', TRUE)
                RETURNING id
                """,
                email.lower(),
                password_hash,
                full_name,
                org_id
            )

            print(f"✓ Admin user created successfully!")
            print(f"  User ID: {user_id}")
            print(f"  Organization ID: {org_id}")

        print(f"\n{'='*60}")
        print(f"ADMIN CREDENTIALS")
        print(f"{'='*60}")
        print(f"Email:    {email}")
        print(f"Password: {password}")
        print(f"{'='*60}")
        print(f"\nPlease change your password after first login!")
        print(f"\nYou can now login at: https://smartgnosis.com")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_admin_user())
