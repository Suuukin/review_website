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
        background = review_data["background"]
        genres = json.dumps(review_data.get("genres", []))
        extra = json.dumps(review_data)

        # Extract new metadata columns
        name = review_data.get("name")
        developers = json.dumps(review_data.get("developers", []))
        publishers = json.dumps(review_data.get("publishers", []))

        recommendations = review_data.get("recommendations")
        recommendations_count = (
            recommendations["total"] if isinstance(recommendations, dict) else None
        )

        is_free = 1 if review_data.get("is_free") else 0

        price = review_data.get("price_overview")
        if isinstance(price, dict):
            price_currency = price.get("currency")
            price_initial = price.get("initial")
            price_final = price.get("final")
            price_discount_percent = price.get("discount_percent", 0)
        else:
            price_currency = None
            price_initial = None
            price_final = None
            price_discount_percent = 0

        # Note: reviews_positive/reviews_negative come from a different API endpoint
        # and can't be extracted from the cached data. They will be populated
        # on first refresh via refresh_steam_data().

        conn.execute(
            """INSERT INTO app_info (
                app_id, detailed_description, header_image, genres, background, extra,
                name, developers, publishers, recommendations_count, is_free,
                price_currency, price_initial, price_final, price_discount_percent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                app_id, detailed_description, header_image, genres, background, extra,
                name, developers, publishers, recommendations_count, is_free,
                price_currency, price_initial, price_final, price_discount_percent,
            ),
        )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
