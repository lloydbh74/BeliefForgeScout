from datetime import datetime
import os
import sqlite3
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
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scout.db'))
print(f"Using SQLite database at: {SQLITE_DB_PATH}")

def format_date(value):
    if isinstance(value, int) or isinstance(value, float):
        # Handle unix timestamp
        return datetime.fromtimestamp(value).isoformat()
    return value

def fetch_sqlite_data(query, params=()):
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
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

def migrate_table(sqlite_table, supabase_table, date_cols=[], filter_orphans=False):
    print(f"Migrating {sqlite_table} to {supabase_table}...")
    rows = fetch_sqlite_data(f"SELECT * FROM {sqlite_table}")
    if not rows:
        print("  No rows found.")
        return

    if filter_orphans:
        print("  Filtering orphaned records...")
        valid_ids = {r['post_id'] for r in fetch_sqlite_data("SELECT post_id FROM briefings")}
        rows = [r for r in rows if r.get('post_id') in valid_ids]
        print(f"  Rows remaining after filtering: {len(rows)}")

    # Process dates
    for row in rows:
        for col in date_cols:
            if col in row and row[col]:
                row[col] = format_date(row[col])

    # Supabase insert
    try:
        response = supabase.table(supabase_table).upsert(rows).execute()
        print(f"  Successfully migrated {len(response.data)} rows.")
    except Exception as e:
        print(f"  Error migrating {supabase_table}: {e}")

if __name__ == "__main__":
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"SQLite DB not found at {SQLITE_DB_PATH}.")
        exit(1)
        
    print("Starting Migration from SQLite to Supabase...\n")
    migrate_table("processed_posts", "scout_processed_posts", ["processed_at"])
    migrate_table("briefings", "scout_briefings", ["created_at", "post_created_at"])
    migrate_table("engagements", "scout_engagements", ["posted_at", "last_updated"], filter_orphans=True)
    print("\nMigration Script Finished.")
