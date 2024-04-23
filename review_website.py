from flask import Flask, render_template, request, flash, redirect, url_for
import sqlite3
from werkzeug.exceptions import abort

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
            "SELECT * FROM posts WHERE appid = ? AND store = ?", (post_id, store)
        ).fetchone()
    else:
        post = conn.execute(
            "SELECT * FROM posts WHERE id = ? AND store = ?", (post_id, store)
        ).fetchone()
    conn.close()
    print(store, post_id)
    if post is None:
        abort(404)
    return post


@app.route("/<string:store>/<int:post_id>")
def post(post_id, store):
    post = get_post(post_id, store)
    if post["store"] == "steam":
        store_url = f"https://steampowered.com/app/{post['appid']}"
    else:
        store_url = None
    return render_template("post.html", post=post, store_url=store_url)


@app.route("/")
def index():
    conn = get_db_connection()
    posts = conn.execute("SELECT * FROM posts").fetchall()
    conn.close()

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
    post = get_post(id, store)

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
    post = get_post(id, store)
    conn = get_db_connection()
    conn.execute("DELETE FROM posts WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash('"{}" was successfully deleted!'.format(post["title"]))
    return redirect(url_for("index"))
