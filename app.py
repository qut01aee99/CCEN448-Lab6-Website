
import os
import sqlite3
from functools import wraps

from flask import (
    Flask, flash, redirect, render_template_string,
    request, session, url_for
)
from werkzeug.security import (
    generate_password_hash, check_password_hash
)

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY", "local-development-only-change-me"
)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

DATABASE = os.environ.get(
    "DATABASE_PATH",
    os.path.join(os.path.dirname(__file__), "tasks.db")
)

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db

def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

STYLE = """
<style>
body {
    font-family: Arial, sans-serif;
    background: #f1f5f9;
    margin: 0;
    color: #1e293b;
}
nav {
    background: #172554;
    color: white;
    padding: 18px 8%;
}
nav a { color: white; margin-right: 20px; }
.container {
    max-width: 680px;
    margin: 50px auto;
    background: white;
    padding: 35px;
    border-radius: 12px;
    box-shadow: 0 4px 20px #0001;
}
input, button {
    padding: 12px;
    margin: 8px 0;
    box-sizing: border-box;
}
input { width: 100%; border: 1px solid #cbd5e1; }
button {
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 5px;
    cursor: pointer;
}
a { color: #2563eb; }
.task {
    padding: 15px;
    border-bottom: 1px solid #e2e8f0;
}
.message { color: #b91c1c; }
</style>
"""

BASE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>CCEN448 Student Task Manager</title>
""" + STYLE + """
</head>
<body>
<nav>
<strong>CCEN448 Student Task Manager</strong>
{% if session.get('user_id') %}
<span style="float:right">
{{ session['username'] }} |
<a href="{{ url_for('logout') }}">Logout</a>
</span>
{% endif %}
</nav>
<div class="container">
{% for message in get_flashed_messages() %}
<p class="message">{{ message }}</p>
{% endfor %}
"""

def page(content, **context):
    return render_template_string(
        BASE + content + "</div></body></html>",
        **context
    )

def login_required(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return function(*args, **kwargs)
    return wrapped

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return page("""
        <h1>Welcome to Student Task Manager</h1>
        <p>A dynamic Flask website using SQLite.</p>
        <p>Manage your student tasks securely.</p>
        <a href="/register">Register</a> |
        <a href="/login">Login</a>
    """)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or len(password) < 8:
            flash("Enter a username and password of at least 8 characters.")
        else:
            try:
                with get_db() as db:
                    db.execute(
                        "INSERT INTO users (username, password_hash) "
                        "VALUES (?, ?)",
                        (username, generate_password_hash(password))
                    )
                flash("Registration successful. Please log in.")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Username already exists.")

    return page("""
        <h2>Create Account</h2>
        <form method="post">
            <input name="username" placeholder="Username"
                   required maxlength="80">
            <input type="password" name="password"
                   placeholder="Password (8+ characters)"
                   required minlength="8">
            <button type="submit">Register</button>
        </form>
        <p>Already registered? <a href="/login">Login</a></p>
    """)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        with get_db() as db:
            user = db.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            ).fetchone()

        if user and check_password_hash(
            user["password_hash"], password
        ):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.")

    return page("""
        <h2>Student Login</h2>
        <form method="post">
            <input name="username" placeholder="Username" required>
            <input type="password" name="password"
                   placeholder="Password" required>
            <button type="submit">Login</button>
        </form>
        <p>No account? <a href="/register">Register</a></p>
    """)

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST":
        title = request.form.get("title", "").strip()

        if title and len(title) <= 200:
            with get_db() as db:
                db.execute(
                    "INSERT INTO tasks (user_id, title) VALUES (?, ?)",
                    (session["user_id"], title)
                )
            flash("Task saved to database.")
        return redirect(url_for("dashboard"))

    with get_db() as db:
        tasks = db.execute(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY id DESC",
            (session["user_id"],)
        ).fetchall()

    return page("""
        <h1>Student Dashboard</h1>
        <p>Logged in as <strong>{{ session['username'] }}</strong></p>
        <h3>Add a New Task</h3>
        <form method="post">
            <input name="title" placeholder="Enter a student task"
                   required maxlength="200">
            <button type="submit">Save Task</button>
        </form>
        <h3>My Tasks ({{ tasks|length }})</h3>
        {% for task in tasks %}
            <div class="task">
                {{ task['title'] }}
            </div>
        {% else %}
            <p>No tasks yet. Add your first task!</p>
        {% endfor %}
    """, tasks=tasks)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
