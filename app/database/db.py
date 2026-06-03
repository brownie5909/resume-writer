import sqlite3
from contextlib import contextmanager

# Database setup
DB_PATH = "hire_ready.db"

def init_database():
    """Initialize SQLite database with required tables"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Users table
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
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS resume_documents (
            document_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
    
            title TEXT NOT NULL,
    
            resume_text TEXT,
            cover_letter_text TEXT,
    
            template TEXT DEFAULT 'default',
            pdf_filename TEXT,
    
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
        
        # Other tables...
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
        
        conn.commit()

    @contextmanager
    def get_db():
        """Database connection context manager"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    CREATE TABLE IF NOT EXISTS resume_versions (
        version_id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
    
        title TEXT,
        resume_text TEXT,
        cover_letter_text TEXT,
        template TEXT,
    
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
        FOREIGN KEY(document_id) REFERENCES resume_documents(document_id),
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )
