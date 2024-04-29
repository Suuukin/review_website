DROP TABLE IF EXISTS posts;

CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    app_id INTEGER,
    store TEXT DEFAULT "other"
);

DROP TABLE IF EXISTS app_info;

CREATE TABLE app_info (
    app_id INTEGER PRIMARY KEY,
    detailed_description Text,
    header_image TEXT,
    genres TEXT,
    background TEXT,
    extra TEXT
);