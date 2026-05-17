import sqlite3

connection = sqlite3.connect("database.db")

cur = connection.cursor()

cur.execute("DROP TABLE IF EXISTS tags")

cur.execute(
    """CREATE TABLE tags (
    tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    color TEXT
    )"""
)

cur.execute("DROP TABLE IF EXISTS posts_tags")

cur.execute("DROP TABLE IF EXISTS tag_relations")

cur.execute(
    """CREATE TABLE posts_tags (
    post_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL
    )"""
)

cur.execute("INSERT INTO tags (title) VALUES (?)", ("Great",))

cur.execute("INSERT INTO tags (title) VALUES (?)", ("Bad",))

cur.execute("INSERT INTO posts_tags (post_id, tag_id) VALUES (?, ?)", ("2", "1"))

cur.execute("INSERT INTO posts_tags (post_id, tag_id) VALUES (?, ?)", ("2", "2"))

cur.execute("INSERT INTO posts_tags (post_id, tag_id) VALUES (?, ?)", ("3", "1"))

test = connection.execute("SELECT * FROM tags").fetchall()

print(test)

connection.commit()
connection.close()
