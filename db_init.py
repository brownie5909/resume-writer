#!/usr/bin/env python3
"""
Database initialization script for Hire Ready Enhanced
Run this script to set up the SQLite database with required tables
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = "hire_ready.db"

def create_database():
    """Create the database and all required tables"""
    
    print("🗄️  Initializing Hire Ready Enhanced database...")
    
    # Create database connection
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Users table
        print("📝 Creating users table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                tier TEXT DEFAULT 'free',
                is_verified BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                is_admin BOOLEAN DEFAULT FALSE
            )
        """)
        
        # Email verification tokens
        print("📧 Creating email verification tokens table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS email_verification_tokens (
                token_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Password reset tokens
        print("🔑 Creating password reset tokens table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                token_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # User sessions for tracking
        print("🔐 Creating user sessions table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                refresh_token_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # Usage tracking table
        print("📊 Creating usage tracking table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_tracking (
                usage_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                usage_count INTEGER DEFAULT 0,
                month_year TEXT NOT NULL,
                last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                UNIQUE(user_id, feature_name, month_year)
            )
        """)
        
        # Admin audit log table
        print("🔍 Creating admin audit log table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_audit_log (
                log_id TEXT PRIMARY KEY,
                admin_user_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_user_id) REFERENCES users (user_id)
            )
        """)
        
        # Create indexes for better performance
        print("🚀 Creating database indexes...")
        
        # Users indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_tier ON users(tier)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)")
        
        # Token indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_tokens_user ON email_verification_tokens(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_tokens_hash ON email_verification_tokens(token_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_password_tokens_user ON password_reset_tokens(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_password_tokens_hash ON password_reset_tokens(token_hash)")
        
        # Session indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(refresh_token_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_active ON user_sessions(is_active)")
        
        # Usage tracking indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_user ON usage_tracking(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_feature ON usage_tracking(feature_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_month ON usage_tracking(month_year)")
        
        # Audit log indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_admin ON admin_audit_log(admin_user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_date ON admin_audit_log(created_at)")
        
        # Commit all changes
        conn.commit()
        
        print("✅ Database initialized successfully!")
        print(f"📍 Database location: {os.path.abspath(DB_PATH)}")
        
        # Show table info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"📋 Created {len(tables)} tables:")
        for table in tables:
            print(f"   - {table[0]}")
            
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def create_test_user():
    """Create a test user for development"""
    try:
        from passlib.context import CryptContext
        import uuid
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        user_id = str(uuid.uuid4())
        email = "test@hireready.com"
        password_hash = pwd_context.hash("testpass123")
        full_name = "Test User"
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO users (user_id, email, password_hash, full_name, tier, is_verified)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, email, password_hash, full_name, "free", True))
            
            conn.commit()
            print(f"👤 Test user created:")
            print(f"   Email: {email}")
            print(f"   Password: testpass123")
            print(f"   User ID: {user_id}")
            
        except Exception as e:
            print(f"❌ Error creating test user: {e}")
        finally:
            conn.close()
            
    except ImportError:
        print("⚠️ Passlib not available, skipping test user creation")
        print("   Install with: pip install passlib[bcrypt]")

def create_admin_user():
    """Create an admin user for management"""
    try:
        from passlib.context import CryptContext
        import uuid
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        user_id = str(uuid.uuid4())
        email = "admin@hireready.com"
        password_hash = pwd_context.hash("admin123")
        full_name = "Admin User"
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO users (user_id, email, password_hash, full_name, tier, is_verified, is_admin)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, email, password_hash, full_name, "professional", True, True))
            
            conn.commit()
            print(f"👑 Admin user created:")
            print(f"   Email: {email}")
            print(f"   Password: admin123")
            print(f"   User ID: {user_id}")
            
        except Exception as e:
            print(f"❌ Error creating admin user: {e}")
        finally:
            conn.close()
            
    except ImportError:
        print("⚠️ Passlib not available, skipping admin user creation")

def show_database_info():
    """Show information about the database"""
    if not os.path.exists(DB_PATH):
        print("❌ Database does not exist. Run create_database() first.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        print(f"📊 Database Information:")
        print(f"   Location: {os.path.abspath(DB_PATH)}")
        print(f"   Size: {os.path.getsize(DB_PATH)} bytes")
        
        # Count records in each table
        tables = ["users", "email_verification_tokens", "password_reset_tokens", "user_sessions", "usage_tracking", "admin_audit_log"]
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   {table}: {count} records")
            except sqlite3.Error:
                print(f"   {table}: table not found")
        
    except Exception as e:
        print(f"❌ Error reading database info: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "create":
            create_database()
        elif command == "test-user":
            create_test_user()
        elif command == "admin-user":
            create_admin_user()
        elif command == "info":
            show_database_info()
        elif command == "reset":
            if os.path.exists(DB_PATH):
                os.remove(DB_PATH)
                print("🗑️  Database deleted")
            create_database()
            create_test_user()
            create_admin_user()
        else:
            print("Usage: python db_init.py [create|test-user|admin-user|info|reset]")
    else:
        # Default: create database and users
        create_database()
        
        # Ask if user wants to create test users
        response = input("📝 Create test user and admin user for development? (y/n): ")
        if response.lower().startswith('y'):
            create_test_user()
            create_admin_user()
        
        show_database_info()
        print("\n🎉 Database setup complete!")
        print("Next step: Copy the route files and run the API server")