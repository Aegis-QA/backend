"""
Quick migration to add image_paths column to jobs table
"""
import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/testcase_db")

# Parse connection string
conn_params = {
    'dbname': 'testcase_db',
    'user': 'user',
    'password': 'password',
    'host': 'localhost',
    'port': 5432
}

try:
    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()
    
    # Add image_paths column if it doesn't exist
    cur.execute("""
        ALTER TABLE jobs 
        ADD COLUMN IF NOT EXISTS image_paths JSON;
    """)
    
    conn.commit()
    print("✅ Successfully added image_paths column to jobs table")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Migration failed: {e}")
