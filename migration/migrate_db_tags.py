"""
Migration script: updates database from the old schema (revision 02578f7)
to the current schema.

Old schema had:
    - tag_relations table (instead of posts_tags)
    - tags table (same as current)
    - posts, app_info tables (same)

Changes:
    - Rename tag_relations -> posts_tags
    - Create tags and posts_tags if missing entirely
"""

import sqlite3
import sys

DB_PATH = "database.db"


def migrate(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Check what tables exist
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing = {row[0] for row in c.fetchall()}
    print(f"Existing tables: {existing}")

    if "posts_tags" in existing:
        print("✓ posts_tags already exists — nothing to do.")
        conn.close()
        return

    if "tag_relations" in existing:
        print("→ Renaming tag_relations → posts_tags ...")
        c.execute("ALTER TABLE tag_relations RENAME TO posts_tags")
        conn.commit()
        print("✓ Done.")
    else:
        print("→ Neither tag_relations nor posts_tags found.")
        print("→ Creating posts_tags table ...")
        c.execute("""
            CREATE TABLE posts_tags (
                post_id INTEGER NOT NULL,
                tag_id INTEGER NOT NULL
            )
        """)
        conn.commit()
        print("✓ Created posts_tags.")

    # Ensure tags table exists (it should, but be safe)
    if "tags" not in existing:
        print("→ Creating tags table ...")
        c.execute("""
            CREATE TABLE tags (
                tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                color TEXT
            )
        """)
        conn.commit()
        print("✓ Created tags.")

    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = DB_PATH
    migrate(db_path)
