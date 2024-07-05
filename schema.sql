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
    detailed_description TEXT,
    header_image TEXT,
    genres TEXT,
    background TEXT,
    extra TEXT
);

DROP TABLE IF EXISTS tags;

CREATE TABLE tags (
    tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    color TEXT
);

DROP TABLE IF EXISTS tag_relations;

CREATE TABLE tag_relations (
    post_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
);