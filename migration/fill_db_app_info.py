import sqlite3
from pathlib import Path
import json


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def main():
    steam_data = Path("steam_data")

    conn = get_db_connection()

    for fn in steam_data.glob("*.json"):
        with open(fn) as fp:
            review_data = json.load(fp)

        app_id = review_data["steam_appid"]
        detailed_description = review_data["detailed_description"]
        header_image = review_data["header_image"]
        genres = json.dumps(review_data.get("genres", []))
        background = review_data["background"]
        extra = json.dumps(review_data)

        conn.execute(
            "INSERT INTO app_info (app_id, detailed_description, header_image, genres, background, extra) VALUES (?, ?, ?, ?, ?, ?)",
            (app_id, detailed_description, header_image, genres, background, extra),
        )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
