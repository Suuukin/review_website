import sqlite3
import yaml


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def main():
    with open("reviews.yaml") as fp:
        data = yaml.load(fp, Loader=yaml.Loader)

    conn = get_db_connection()
    for item in data:
        title = item["title"]
        content = item["content"]
        appid = item["appid"]
        store = item["store"]
        conn.execute(
            "INSERT INTO posts (title, content, appid, store) VALUES (?, ?, ?, ?)",
            (title, content, appid, store),
        )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
