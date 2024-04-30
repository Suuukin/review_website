from flask import Flask, render_template, request, flash, redirect, url_for
import sqlite3
from werkzeug.exceptions import abort
import json

app = Flask(__name__)
app.config["SECRET_KEY"] = "example"


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


def get_post(post_id, store):
    conn = get_db_connection()
    if store == "steam":
        post = conn.execute(
            "SELECT * FROM posts WHERE app_id = ? AND store = ?", (post_id, store)
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


@app.route("/<string:store>/<int:post_id>")
def post(post_id, store):
    post, app_info = get_post(post_id, store)
    if post["store"] == "steam":
        store_url = f"https://steampowered.com/app/{post['app_id']}"
        steam_image = app_info["header_image"]
        bg_img = app_info["background"]
        app_info_extra = json.loads(app_info["extra"])
        #desc = app_info_extra["short_description"]
        desc = app_info["detailed_description"]
        return render_template(
            "steam_post.html", post=post, store_url=store_url, image=steam_image, bg_img = bg_img, desc = desc
        )
    else:
        store_url = None
    return render_template("post.html", post=post, store_url=store_url)


@app.route("/")
def index():
    conn = get_db_connection()
    post_sql = conn.execute(
        "SELECT posts.*, app_info.extra FROM posts JOIN app_info ON posts.app_id=app_info.app_id"
    ).fetchall()
    conn.close()

    posts = []
    for row in post_sql:
        post = dict((k, row[k]) for k in row.keys())
        post["extra"] = json.loads(post["extra"])
        post["genres"] = [g["description"] for g in post["extra"].get("genres", [])]
        posts.append(post)

    return render_template("index.html", posts=posts)


@app.route("/create", methods=("GET", "POST"))
def create():
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]

        if not title:
            flash("Title is required")
        else:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO posts (title, content) VALUES (?, ?)", (title, content)
            )
            conn.commit()
            conn.close()
            return redirect(url_for("index"))

    return render_template("create.html")


@app.route("/<string:store>/<int:id>/edit", methods=("GET", "POST"))
def edit(store, id):
    post, app_info = get_post(id, store)

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]

        if not title:
            flash("Title is required!")
        else:
            conn = get_db_connection()
            conn.execute(
                "UPDATE posts SET title = ?, content = ?" " WHERE id = ?",
                (title, content, id),
            )
            conn.commit()
            conn.close()
            return redirect(url_for("index"))

    return render_template("edit.html", post=post)


@app.route("/<string:store>/<int:id>/delete", methods=("POST",))
def delete(store, id):
    post, app_info = get_post(id, store)
    conn = get_db_connection()
    conn.execute("DELETE FROM posts WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash('"{}" was successfully deleted!'.format(post["title"]))
    return redirect(url_for("index"))
