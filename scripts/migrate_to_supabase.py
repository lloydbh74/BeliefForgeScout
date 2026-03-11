import sqlite3
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from scout/.env
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scout', '.env')
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set in the .env file.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Define path to SQLite DB
SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scout.db')

def fetch_sqlite_data(query, params=()):
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        # return rows as dictionaries
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error fetching data from SQLite: {e}")
        return []
    finally:
        if conn:
            conn.close()

def migrate_processed_posts():
    print("Migrating scout_processed_posts...")
    rows = fetch_sqlite_data("SELECT * FROM processed_posts")
    if not rows:
        print("  No rows found.")
        return
    
    # Supabase insert
    try:
        response = supabase.table("scout_processed_posts").upsert(rows).execute()
        print(f"  Successfully migrated {len(response.data)} rows.")
    except Exception as e:
        print(f"  Error migrating scout_processed_posts: {e}")

def migrate_briefings():
    print("Migrating scout_briefings...")
    rows = fetch_sqlite_data("SELECT * FROM briefings")
    if not rows:
        print("  No rows found.")
        return
    
    try:
        response = supabase.table("scout_briefings").upsert(rows).execute()
        print(f"  Successfully migrated {len(response.data)} rows.")
    except Exception as e:
        print(f"  Error migrating scout_briefings: {e}")

def migrate_engagements():
    print("Migrating scout_engagements...")
    rows = fetch_sqlite_data("SELECT * FROM engagements")
    if not rows:
        print("  No rows found.")
        return
    
    try:
        response = supabase.table("scout_engagements").upsert(rows).execute()
        print(f"  Successfully migrated {len(response.data)} rows.")
    except Exception as e:
        print(f"  Error migrating scout_engagements: {e}")

if __name__ == "__main__":
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"SQLite DB not found at {SQLITE_DB_PATH}. Ensure the path is correct before running the migration.")
        exit(1)
        
    print("Starting Migration from SQLite to Supabase...\n")
    migrate_processed_posts()
    migrate_briefings()
    migrate_engagements()
    print("\nMigration Script Finished.")
