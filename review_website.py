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
import sqlite3
from werkzeug.exceptions import abort
import json
import os
import markdown

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


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
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


@app.route("/<string:store>/<int:post_id>")
def post(post_id, store):
    post, app_info = get_post(post_id, store)
    post_content = render_markdown(post["content"])
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
        )
    else:
        store_url = None
    return render_template("post.j2", post=post, post_content=post_content, store_url=store_url)


@app.route("/")
def index():
    conn = get_db_connection()
    post_sql = conn.execute(
        "SELECT posts.*, app_info.extra FROM posts LEFT JOIN app_info ON posts.app_id=app_info.app_id"
    ).fetchall()

    posts = []
    for row in post_sql:
        post = dict((k, row[k]) for k in row.keys())
        if row["extra"]:
            post["extra"] = json.loads(post["extra"])
            post["genres"] = [g["description"] for g in post["extra"].get("genres", [])]

        post_id = post["id"]
        tags = conn.execute(
            "SELECT title, color FROM posts_tags JOIN tags ON posts_tags.tag_id = tags.tag_id WHERE posts_tags.post_id=?", (post_id,)
        ).fetchall()

        post["tags"] = tags

        posts.append(post)

    conn.close()

    return render_template("index.j2", posts=posts)


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

        if not title:
            flash("Title is required")
        else:
            print("create post")
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO posts (title, content, app_id, store) VALUES (?, ?, ?, ?)",
                (title, content, app_id, store),
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
    rows = conn.execute(
        """SELECT app_id, header_image, extra
           FROM app_info
           WHERE json_extract(extra, '$.name') LIKE ?
           ORDER BY app_id
           LIMIT 20""",
        (f"%{q}%",),
    ).fetchall()
    conn.close()

    results = []
    for row in rows:
        extra = json.loads(row["extra"])
        results.append({
            "app_id": row["app_id"],
            "name": extra.get("name", "Unknown"),
            "header_image": row["header_image"],
            "capsule_image": extra.get("capsule_image", ""),
        })

    return jsonify(results)


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
            conn.commit()
            conn.close()
            return redirect(url_for("index"))

    return render_template("edit.j2", post=post)


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


if __name__ == "__main__":
    app.run()
