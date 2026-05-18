from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    session,
    jsonify,
)
from flask_wtf.csrf import CSRFProtect
import sqlite3
from werkzeug.exceptions import abort
import re
import json
import os
import time
from datetime import datetime, timezone
import markdown
import requests

# flake8: noqa

PRODUCTION = os.environ.get("PRODUCTION") == "1"
DEV = not PRODUCTION

if PRODUCTION:
    users = {os.environ.get("AUTH_USER"): os.environ.get("AUTH_PASS")}
else:
    users = {"dev": "welcome"}


class PrefixMiddleware:
    def __init__(self, app, prefix=""):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        path = environ["PATH_INFO"]
        if environ["PATH_INFO"].startswith(self.prefix):
            environ["PATH_INFO"] = environ["PATH_INFO"][len(self.prefix) :]
            environ["SCRIPT_NAME"] = self.prefix
            return self.app(environ, start_response)
        else:
            print("path", path)
            start_response("404", [("Content-Type", "text/plain")])
            return ["This url does not belong to the app.".encode()]


app = Flask(__name__)
if PRODUCTION:
    app.config["ENV"] = "production"
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
    app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix="/game-reviews")
else:
    app.config["SECRET_KEY"] = "example"

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["WTF_CSRF_TIME_LIMIT"] = None  # token lasts as long as the session
csrf = CSRFProtect(app)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def _sql_regex(pattern, text):
    if text is None:
        return 0
    return 1 if re.search(pattern, text) else 0


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    conn.create_function("regexp", 2, _sql_regex)
    return conn


def get_post(post_id, store):
    conn = get_db_connection()
    if store == "steam":
        post = conn.execute(
            "SELECT * FROM posts WHERE app_id = ? AND store = ?",
            (post_id, store),
        ).fetchone()
        app_info = conn.execute(
            "SELECT * FROM app_info WHERE app_id = ?", (post_id,)
        ).fetchone()
    else:
        post = conn.execute(
            "SELECT * FROM posts WHERE id = ? AND store = ?", (post_id, store)
        ).fetchone()
        app_info = None
    conn.close()

    print(store, post_id)
    if post is None:
        abort(404)

    return post, app_info


def render_markdown(text):
    return markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "codehilite", "toc", "nl2br"],
    )


# In-memory set of app_ids currently being refreshed (avoid duplicate concurrent calls)
_refreshing = set()

# TTL for Steam data refresh (24 hours in seconds)
STEAM_REFRESH_TTL = 24 * 60 * 60


def refresh_steam_data(app_id):
    """Fetch fresh Steam API data for a given app_id and update the database."""
    url = f"https://store.steampowered.com/api/appdetails/?appids={app_id}&cc=CA"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        result = resp.json()

        data = result.get(str(app_id), {}).get("data")
        if not data:
            print(f"Steam API returned no data for app_id={app_id}")
            return

        # Extract fields for dedicated columns
        name = data.get("name")
        developers = json.dumps(data.get("developers", []))
        publishers = json.dumps(data.get("publishers", []))

        recommendations = data.get("recommendations")
        recommendations_count = (
            recommendations["total"] if isinstance(recommendations, dict) else None
        )

        is_free = 1 if data.get("is_free") else 0

        price = data.get("price_overview")
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

        # Fetch review counts from Steam reviews API (different endpoint)
        reviews_positive = None
        reviews_negative = None
        try:
            reviews_url = f"https://store.steampowered.com/appreviews/{app_id}?json=1&language=all&filter=summary"
            reviews_resp = requests.get(reviews_url, timeout=10)
            reviews_resp.raise_for_status()
            reviews_data = reviews_resp.json()
            query_summary = reviews_data.get("query_summary", {})
            if query_summary.get("total_reviews", 0) > 0:
                reviews_positive = query_summary.get("total_positive", 0)
                reviews_negative = query_summary.get("total_negative", 0)
        except requests.RequestException as e:
            print(f"Steam reviews API error for app_id={app_id}: {e}")
        except (KeyError, ValueError, TypeError) as e:
            print(f"Steam reviews data parse error for app_id={app_id}: {e}")

        # Re-serialize full response as extra
        extra = json.dumps(data)

        # Grab other fields we already store as columns
        detailed_description = data.get("detailed_description", "")
        header_image = data.get("header_image", "")
        background = data.get("background", "")
        genres = json.dumps(data.get("genres", []))

        conn = get_db_connection()
        conn.execute(
            """INSERT OR REPLACE INTO app_info (
                app_id, name, developers, publishers,
                recommendations_count, is_free,
                price_currency, price_initial, price_final,
                price_discount_percent, price_updated_at,
                reviews_positive, reviews_negative,
                extra, detailed_description, header_image,
                background, genres
            ) VALUES (
                ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                ?, CURRENT_TIMESTAMP,
                ?, ?,
                ?, ?, ?,
                ?, ?
            )""",
            (
                app_id,
                name,
                developers,
                publishers,
                recommendations_count,
                is_free,
                price_currency,
                price_initial,
                price_final,
                price_discount_percent,
                reviews_positive,
                reviews_negative,
                extra,
                detailed_description,
                header_image,
                background,
                genres,
            ),
        )
        conn.commit()
        conn.close()
        print(f"Refreshed Steam data for app_id={app_id}")

    except requests.RequestException as e:
        print(f"Steam API error for app_id={app_id}: {e}")
    except (KeyError, ValueError, TypeError) as e:
        print(f"Steam data parse error for app_id={app_id}: {e}")


def refresh_if_needed(app_info):
    """Check if Steam data is stale and trigger a refresh if so.
    Returns True if a refresh was attempted, False otherwise."""
    if app_info is None:
        return False

    app_id = app_info["app_id"]

    # Check if already being refreshed by another request
    if app_id in _refreshing:
        print(f"Skipping refresh for app_id={app_id}: already in progress")
        return False

    # Check staleness
    try:
        price_updated = app_info["price_updated_at"]
    except (KeyError, IndexError):
        price_updated = None
    if price_updated is not None:
        try:
            # SQLite's CURRENT_TIMESTAMP returns UTC, so compare against UTC now
            updated = datetime.fromisoformat(price_updated).replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - updated).total_seconds()
            if age < STEAM_REFRESH_TTL:
                print(f"Skipping refresh for app_id={app_id}: data is still fresh (age={age:.0f}s)")
                return False  # still fresh
        except (ValueError, TypeError):
            pass  # couldn't parse timestamp, treat as stale

    # Trigger refresh
    print(f"Triggering refresh for app_id={app_id}")
    _refreshing.add(app_id)
    try:
        refresh_steam_data(app_id)
        return True
    finally:
        _refreshing.discard(app_id)


def parse_search_query(query):
    """Parse a search query into a list of (token, is_quoted) tuples."""
    results = []
    for matched in re.finditer(r'"([^"]+)"|(\S+)', query):
        if matched.group(1):  # quoted phrase
            results.append((matched.group(1), True))
        else:  # bare word
            results.append((matched.group(2), False))
    return results


def build_pagination(current_page, total_pages):
    """Build a pagination data structure for the template.
    Returns a dict with:
      - page: current page number
      - total_pages: total number of pages
      - prev_page: previous page number, or None
      - next_page: next page number, or None
      - pages: list of page elements — each is an int (page number) or None (ellipsis)
    """
    if total_pages <= 1:
        return None

    def _get_range():
        """Return a list where each entry is an int (page) or None (ellipsis)."""
        # Show at most 7 items: first, last, current +/- 2, and ellipses as needed
        pages = []
        # Always include page 1
        pages.append(1)

        start = max(2, current_page - 2)
        end = min(total_pages - 1, current_page + 2)

        if start > 2:
            pages.append(None)  # ellipsis

        for p in range(start, end + 1):
            pages.append(p)

        if end < total_pages - 1:
            pages.append(None)  # ellipsis

        # Always include last page if > 1
        if total_pages > 1:
            pages.append(total_pages)

        return pages

    return {
        "page": current_page,
        "total_pages": total_pages,
        "prev_page": current_page - 1 if current_page > 1 else None,
        "next_page": current_page + 1 if current_page < total_pages else None,
        "pages": _get_range(),
    }


@app.template_filter("highlight")
def highlight_filter(text, query):
    """Wrap search term matches in <mark> tags."""
    if not query or not text:
        return text
    tokens = parse_search_query(query)
    patterns = []
    for token, is_quoted in tokens:
        if is_quoted:
            patterns.append(re.escape(token))
        else:
            patterns.append(r"\b" + re.escape(token))
    if not patterns:
        return text
    combined = "(?i)(" + "|".join(patterns) + ")"
    return re.sub(combined, r"<mark>\1</mark>", text)


@app.route("/<string:store>/<int:post_id>")
def post(post_id, store):
    post, app_info = get_post(post_id, store)
    post_content = render_markdown(post["content"])

    # Refresh Steam data if stale
    if store == "steam" and app_info is not None:
        refreshed = refresh_if_needed(app_info)
        if refreshed:
            # Re-fetch app_info to get fresh data
            conn = get_db_connection()
            app_info = conn.execute(
                "SELECT * FROM app_info WHERE app_id = ?", (post_id,)
            ).fetchone()
            conn.close()

    conn = get_db_connection()
    tags = conn.execute(
        "SELECT tags.title, tags.color FROM posts_tags JOIN tags ON posts_tags.tag_id = tags.tag_id WHERE posts_tags.post_id = ?",
        (post["id"],),
    ).fetchall()
    conn.close()

    if post["store"] == "steam":
        store_url = f"https://steampowered.com/app/{post['app_id']}"
        steam_image = app_info["header_image"]
        bg_img = app_info["background"]
        desc = app_info["detailed_description"]
        return render_template(
            "steam_post.j2",
            post=post,
            post_content=post_content,
            store_url=store_url,
            image=steam_image,
            bg_img=bg_img,
            desc=desc,
            tags=tags,
            app_info=app_info,
        )
    else:
        store_url = None
    return render_template("post.j2", post=post, post_content=post_content, store_url=store_url, tags=tags)


@app.route("/")
def index():
    query = request.args.get("q", "").strip()
    tokens = parse_search_query(query)

    per_page = 20
    page = request.args.get("page", 1, type=int)
    if page < 1:
        page = 1

    conn = get_db_connection()

    if tokens:
        conditions = []
        params = []
        for token, is_quoted in tokens:
            if is_quoted:
                # Quoted phrase — match anywhere as a substring
                like = f"%{token}%"
                conditions.append(
                    "(posts.title LIKE ? OR posts.id IN (SELECT posts_tags.post_id FROM posts_tags "
                    "JOIN tags ON posts_tags.tag_id = tags.tag_id WHERE tags.title LIKE ?) "
                    "OR app_info.genres LIKE ?)"
                )
                params.extend([like, like, like])
            else:
                # Unquoted word — match from the start of a word (word boundary)
                pattern = r"(?i)\b" + re.escape(token)
                conditions.append(
                    "(posts.title REGEXP ? OR posts.id IN (SELECT posts_tags.post_id FROM posts_tags "
                    "JOIN tags ON posts_tags.tag_id = tags.tag_id WHERE tags.title REGEXP ?) "
                    "OR app_info.genres REGEXP ?)"
                )
                params.extend([pattern, pattern, pattern])

        where_clause = " AND ".join(conditions)

        # Count total matching posts
        count_sql = f"""
            SELECT COUNT(*) FROM posts
            LEFT JOIN app_info ON posts.app_id = app_info.app_id
            WHERE {where_clause}
        """
        total = conn.execute(count_sql, params).fetchone()[0]
    else:
        total = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]

    total_pages = max(1, (total + per_page - 1) // per_page)
    if page > total_pages:
        page = total_pages
    offset = (page - 1) * per_page

    if tokens:
        sql = f"""
            SELECT posts.*, app_info.extra, app_info.is_free, app_info.price_currency, app_info.price_final,
                   app_info.price_initial, app_info.price_discount_percent,
                   app_info.reviews_positive, app_info.reviews_negative
            FROM posts
            LEFT JOIN app_info ON posts.app_id = app_info.app_id
            WHERE {where_clause}
            ORDER BY posts.created DESC
            LIMIT ? OFFSET ?
        """
        post_sql = conn.execute(sql, params + [per_page, offset]).fetchall()
    else:
        post_sql = conn.execute(
            "SELECT posts.*, app_info.extra, app_info.is_free, app_info.price_currency, app_info.price_final, "
            "app_info.price_initial, app_info.price_discount_percent, "
            "app_info.reviews_positive, app_info.reviews_negative FROM posts "
            "LEFT JOIN app_info ON posts.app_id = app_info.app_id "
            "ORDER BY posts.created DESC LIMIT ? OFFSET ?",
            (per_page, offset),
        ).fetchall()

    posts = []
    for row in post_sql:
        post = dict((k, row[k]) for k in row.keys())
        if row["extra"]:
            post["extra"] = json.loads(post["extra"])
            post["genres"] = [g["description"] for g in post["extra"].get("genres", [])]
            rd = post["extra"].get("release_date", {})
            post["coming_soon"] = rd.get("coming_soon", False)
            post["release_date"] = rd.get("date", "")
        else:
            post["coming_soon"] = False
            post["release_date"] = ""

        post_id = post["id"]
        tags = conn.execute(
            "SELECT title, color FROM posts_tags JOIN tags ON posts_tags.tag_id = tags.tag_id WHERE posts_tags.post_id=?", (post_id,)
        ).fetchall()

        post["tags"] = tags

        posts.append(post)

    conn.close()

    pagination = build_pagination(page, total_pages)

    return render_template("index.j2", posts=posts, pagination=pagination)


@app.route("/tags")
def tags_page():
    conn = get_db_connection()
    tags = conn.execute(
        """SELECT tags.*, COUNT(posts_tags.post_id) as usage_count
           FROM tags
           LEFT JOIN posts_tags ON tags.tag_id = posts_tags.tag_id
           GROUP BY tags.tag_id
           ORDER BY usage_count DESC, tags.title ASC"""
    ).fetchall()
    conn.close()
    return render_template("tags.j2", tags=tags)


@app.route("/tags/<int:tag_id>/edit", methods=("POST",))
@login_required
def edit_tag(tag_id):
    title = request.form.get("title", "").strip()
    color = request.form.get("color", "").strip()

    if not title:
        flash("Tag title is required.")
        return redirect(url_for("tags_page"))

    conn = get_db_connection()
    conn.execute(
        "UPDATE tags SET title = ?, color = ? WHERE tag_id = ?",
        (title, color, tag_id),
    )
    conn.commit()
    conn.close()
    flash(f'Tag renamed to "{title}".')
    return redirect(url_for("tags_page"))


@app.route("/tags/<int:tag_id>/delete", methods=("POST",))
@login_required
def delete_tag(tag_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM posts_tags WHERE tag_id = ?", (tag_id,))
    conn.execute("DELETE FROM tags WHERE tag_id = ?", (tag_id,))
    conn.commit()
    conn.close()
    flash("Tag deleted.")
    return redirect(url_for("tags_page"))


@app.route("/tags/cleanup", methods=("POST",))
@login_required
def cleanup_tags():
    conn = get_db_connection()
    cur = conn.execute(
        "DELETE FROM posts_tags WHERE post_id NOT IN (SELECT id FROM posts)"
    )
    orphaned_links = cur.rowcount
    cur = conn.execute(
        "DELETE FROM tags WHERE tag_id NOT IN (SELECT tag_id FROM posts_tags)"
    )
    deleted_tags = cur.rowcount
    conn.commit()
    conn.close()
    if deleted_tags or orphaned_links:
        flash(
            f"Cleaned up {deleted_tags} unused tag(s) and {orphaned_links} orphaned link(s)."
        )
    else:
        flash("Nothing to clean up.")
    return redirect(url_for("tags_page"))


@app.route("/about")
def about_page():
    return render_template("about.j2")


@app.route("/login", methods=("GET", "POST"))
def login():
    if session.get("logged_in"):
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in users and users.get(username) == password:
            session["logged_in"] = True
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password")

    return render_template("login.j2")


@app.route("/logout", methods=("POST",))
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("index"))


@app.route("/create", methods=("GET", "POST"))
@login_required
def create():
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        app_id = request.form.get("app_id") or None
        store = request.form.get("store", "other")

        # For game reviews (store == "steam"), auto-generate title from the game name
        if store == "steam" and app_id:
            conn = get_db_connection()
            app_info = conn.execute(
                "SELECT extra FROM app_info WHERE app_id = ?", (app_id,)
            ).fetchone()
            if app_info:
                extra = json.loads(app_info["extra"])
                title = extra.get("name", "Unknown")
            else:
                # Fallback to the full Steam app list
                row = conn.execute(
                    "SELECT name FROM steam_apps WHERE app_id = ?", (app_id,)
                ).fetchone()
                if row:
                    title = row["name"]
            conn.close()

            # Check if this game already has a review
            conn = get_db_connection()
            existing = conn.execute(
                "SELECT id FROM posts WHERE app_id = ? AND store = 'steam'", (app_id,)
            ).fetchone()
            conn.close()
            if existing:
                flash(f'A review for "{title}" already exists. Each game can only have one review.')
                return render_template("create.j2")

            # Fetch Steam API data for games not yet in app_info
            conn = get_db_connection()
            has_app_info = conn.execute(
                "SELECT 1 FROM app_info WHERE app_id = ?", (app_id,)
            ).fetchone()
            conn.close()
            if not has_app_info:
                refresh_steam_data(int(app_id))

        if not title:
            flash("Title is required")
        else:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO posts (title, content, app_id, store) VALUES (?, ?, ?, ?)",
                (title, content, app_id, store),
            )
            post_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            # Process existing tags
            for tag_id in request.form.getlist("tags"):
                if tag_id and tag_id.isdigit():
                    conn.execute(
                        "INSERT INTO posts_tags (post_id, tag_id) VALUES (?, ?)",
                        (post_id, int(tag_id)),
                    )

            # Process new tags
            new_tags_json = request.form.get("new_tags", "")
            if new_tags_json:
                new_tags = json.loads(new_tags_json)
                for nt in new_tags:
                    cur = conn.execute(
                        "INSERT INTO tags (title, color) VALUES (?, ?)",
                        (nt["title"], nt.get("color", "")),
                    )
                    new_tag_id = cur.lastrowid
                    conn.execute(
                        "INSERT INTO posts_tags (post_id, tag_id) VALUES (?, ?)",
                        (post_id, new_tag_id),
                    )

            conn.commit()
            conn.close()
            return redirect(url_for("index"))

    return render_template("create.j2")


@app.route("/api/games/search")
def api_games_search():
    q = request.args.get("q", "").strip()
    if not q or len(q) < 2:
        return jsonify([])

    conn = get_db_connection()
    escaped_q = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    results = []

    # Word-boundary patterns: match at start of name or after space/colon/hyphen/slash
    wb_patterns = [
        f"{escaped_q}%",           # start of string
        f"% {escaped_q}%",         # after space
        f"%:{escaped_q}%",         # after colon
        f"%-{escaped_q}%",         # after hyphen
        f"%/{escaped_q}%",         # after slash
    ]

    def wb_where(col):
        return " OR ".join(f"{col} LIKE ? ESCAPE '\\'" for _ in wb_patterns)

    # 1. Rich results from app_info (have header_image, capsule_image, etc.)
    rich_query = f"""
        SELECT a.app_id, a.header_image, a.extra, game_name,
               CASE WHEN p.id IS NOT NULL THEN 1 ELSE 0 END as has_review
        FROM (
            SELECT *, json_extract(a.extra, '$.name') as game_name
            FROM app_info a
        ) a
        LEFT JOIN posts p ON p.app_id = a.app_id AND p.store = 'steam'
        WHERE ({wb_where('a.game_name')})
        ORDER BY has_review DESC, a.app_id
    """
    rich_rows = conn.execute(rich_query, wb_patterns).fetchall()

    rich_ids = set()
    for row in rich_rows:
        results.append({
            "app_id": row["app_id"],
            "name": row["game_name"],
            "header_image": row["header_image"],
            "capsule_image": json.loads(row["extra"]).get("capsule_image", ""),
            "has_review": bool(row["has_review"]),
        })
        rich_ids.add(row["app_id"])

    # 2. Basic results from steam_apps (exclude games already in app_info)
    basic_where = wb_where("s.name")
    if rich_ids:
        placeholders = ",".join("?" for _ in rich_ids)
        basic_query = f"""
            SELECT s.app_id, s.name,
                   CASE WHEN p.id IS NOT NULL THEN 1 ELSE 0 END as has_review
            FROM steam_apps s
            LEFT JOIN posts p ON p.app_id = s.app_id AND p.store = 'steam'
            WHERE ({basic_where})
              AND s.app_id NOT IN ({placeholders})
            ORDER BY s.name
            LIMIT ?
        """
        basic_params = wb_patterns + list(rich_ids) + [max(0, 20 - len(results))]
    else:
        basic_query = f"""
            SELECT s.app_id, s.name,
                   CASE WHEN p.id IS NOT NULL THEN 1 ELSE 0 END as has_review
            FROM steam_apps s
            LEFT JOIN posts p ON p.app_id = s.app_id AND p.store = 'steam'
            WHERE ({basic_where})
            ORDER BY s.name
            LIMIT 20
        """
        basic_params = wb_patterns

    basic_rows = conn.execute(basic_query, basic_params).fetchall()
    conn.close()

    for row in basic_rows:
        results.append({
            "app_id": row["app_id"],
            "name": row["name"],
            "header_image": None,
            "capsule_image": None,
            "has_review": bool(row["has_review"]),
        })

    return jsonify(results)


@app.route("/api/tags/search")
def api_tags_search():
    q = request.args.get("q", "").strip()
    conn = get_db_connection()
    if q:
        rows = conn.execute(
            "SELECT tag_id, title, color FROM tags WHERE title LIKE ? ORDER BY title LIMIT 20",
            (f"%{q}%",),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT tag_id, title, color FROM tags ORDER BY title LIMIT 50"
        ).fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])


@app.route("/<string:store>/<int:id>/edit", methods=("GET", "POST"))
@login_required
def edit(store, id):
    post, app_info = get_post(id, store)

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]

        if not title:
            flash("Title is required!")
        else:
            conn = get_db_connection()
            if post["store"] == "steam":
                conn.execute(
                    "UPDATE posts SET title = ?, content = ?" " WHERE app_id = ?",
                    (title, content, id),
                )
            else:
                conn.execute(
                    "UPDATE posts SET title = ?, content = ?" " WHERE id = ?",
                    (title, content, id),
                )

            # Update tags: delete all existing tag relations and re-insert
            conn.execute("DELETE FROM posts_tags WHERE post_id = ?", (post["id"],))

            for tag_id in request.form.getlist("tags"):
                if tag_id and tag_id.isdigit():
                    conn.execute(
                        "INSERT INTO posts_tags (post_id, tag_id) VALUES (?, ?)",
                        (post["id"], int(tag_id)),
                    )

            new_tags_json = request.form.get("new_tags", "")
            if new_tags_json:
                new_tags = json.loads(new_tags_json)
                for nt in new_tags:
                    cur = conn.execute(
                        "INSERT INTO tags (title, color) VALUES (?, ?)",
                        (nt["title"], nt.get("color", "")),
                    )
                    new_tag_id = cur.lastrowid
                    conn.execute(
                        "INSERT INTO posts_tags (post_id, tag_id) VALUES (?, ?)",
                        (post["id"], new_tag_id),
                    )

            conn.commit()
            conn.close()
            return redirect(url_for("index"))

    # GET — fetch current tags for pre-populating the form
    conn = get_db_connection()
    post_tags = [
        dict(row)
        for row in conn.execute(
            "SELECT tags.tag_id, tags.title, tags.color FROM posts_tags JOIN tags ON posts_tags.tag_id = tags.tag_id WHERE posts_tags.post_id = ?",
            (post["id"],),
        ).fetchall()
    ]
    conn.close()

    return render_template("edit.j2", post=post, post_tags=post_tags)


@app.route("/<string:store>/<int:id>/delete", methods=("POST",))
@login_required
def delete(store, id):
    post, app_info = get_post(id, store)
    conn = get_db_connection()
    if post["store"] == "steam":
        conn.execute("DELETE FROM posts WHERE app_id = ? AND store = ?", (id, store))
    else:
        conn.execute("DELETE FROM posts WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash('"{}" was successfully deleted!'.format(post["title"]))
    return redirect(url_for("index"))


# ─── Template Filters ───


@app.template_filter("fromjson")
def fromjson_filter(value):
    """Parse a JSON string into a Python object (for use in templates)."""
    if value is None:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


@app.template_filter("format_price")
def format_price_filter(cents, currency="CDN$"):
    """Format a price in cents to a human-readable string."""
    if cents is None:
        return None
    dollars = cents / 100
    return f"{currency} {dollars:,.2f}"


if __name__ == "__main__":
    app.run()
