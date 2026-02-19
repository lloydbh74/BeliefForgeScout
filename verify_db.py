import sqlite3
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from scout.core.db import ScoutDB

def verify_latest():
    db = ScoutDB()
    print(f"Checking DB at: {db.db_path}")
    
    with sqlite3.connect(db.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check total count
        cursor.execute("SELECT count(*) FROM briefings")
        count = cursor.fetchone()[0]
        print(f"Total briefings: {count}")
        
        # Check manual briefings
        cursor.execute("SELECT * FROM briefings WHERE source='manual' ORDER BY created_at DESC LIMIT 5")
        manuals = [dict(row) for row in cursor.fetchall()]
        
        print(f"\nFound {len(manuals)} manual briefings:")
        for m in manuals:
            print(f"- ID: {m['post_id']}")
            print(f"  Title: {m['title']}")
            print(f"  Status: {m['status']}")
            print(f"  Created: {m['created_at']}")
            print(f"  Intent: {m.get('intent', 'N/A')}")
            print(f"  Score: {m.get('score', 'N/A')}")
            print("---")

if __name__ == "__main__":
    verify_latest()
