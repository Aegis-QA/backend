"""
Initialize database schema
Creates all tables defined in models.py
"""
from app.database import engine, Base
from app.models import Job, TestCase

def init_db():
    """Create all database tables"""
    try:
        # Import models to register them with Base
        print("🔄 Creating database tables...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        print("✅ Database initialized successfully!")
        print("   Tables created: jobs, test_cases")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

if __name__ == "__main__":
    init_db()
