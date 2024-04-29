import sqlite3
import yaml


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def main():
    with open("reviews.yaml") as fp:
        review_data = yaml.load(fp, Loader=yaml.Loader)

    conn = get_db_connection()
    for item in review_data:
        title = item["title"]
        content = item["content"]
        app_id = item["app_id"]
        store = item["store"]
        conn.execute(
            "INSERT INTO posts (title, content, app_id, store) VALUES (?, ?, ?, ?)",
            (title, content, app_id, store),
        )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
