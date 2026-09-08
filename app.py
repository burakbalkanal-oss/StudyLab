import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash

# I used AI to understand and debug errors that occurred during the development.
# I used AI to correct typo mistakes.
# I used AI to get suggestions for my website's appearance.

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///study.db")

def login_required(func):
    @wraps(func)
    def wrapper():
        if session.get("user_id"):
            return func()
        else:
            return redirect("/login")
    return wrapper

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session.clear()
        username = request.form.get("username")
        password = request.form.get("password")
        if not username or not password:
            flash("Must enter a username and password")
            return redirect("/login")

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            flash("Invalid username or password.")
            return redirect("/login")
        session["user_id"] = rows[0]["id"]
        return redirect("/")
    else:
        return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        if not username or not password or not confirmation:
            flash("Username and/or password and/or confirmation is blank.")
            return redirect("/register")
        elif confirmation != password:
            flash("Your confirmation does not match your password.")
            return redirect("/register")
        hash = generate_password_hash(password)
        try:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash)
        except:
            flash("This username already exists.")
            return redirect("/register")
        return redirect("/")
    else:
        return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect("/login")

@app.route("/")
@login_required
def index():
    total = db.execute("SELECT COUNT(task) AS t FROM plan WHERE user_id = ? AND due_to = date('now', 'localtime')", session["user_id"])[0]['t']
    remaining = db.execute("SELECT COUNT(task) AS r FROM plan WHERE user_id = ? AND is_completed = 0 AND due_to = date('now', 'localtime')", session["user_id"])[0]['r']
    completed = db.execute("SELECT COUNT(task) AS c FROM plan WHERE user_id = ? AND is_completed = 1 AND due_to = date('now', 'localtime')", session["user_id"])[0]['c']
    try:
        percentage = int((completed / total) * 100)
    except ZeroDivisionError:
        percentage = 0
    username = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])[0]["username"]
    tasks = db.execute("SELECT id, task, subject FROM plan WHERE user_id = ? AND is_completed = 0 AND due_to = date('now', 'localtime')", session["user_id"])
    return render_template("index.html", total=total, remaining=remaining, completed=completed, percentage=percentage, tasks=tasks, username=username)

@app.route("/new_task", methods=["GET", "POST"])
@login_required
def new_task():
    try:
        current_date = db.execute("SELECT date('now', 'localtime')")
        current_date1 = current_date[0]["date('now', 'localtime')"]
    except (IndexError, KeyError):
        flash("Something went wrong.")
        return redirect("/")
    if request.method == "POST":
        subject = request.form.get("subject")
        task = request.form.get("task")
        date = request.form.get("date")
        if not subject or not task or not date:
            flash("Please fill in all the blanks.")
            return redirect("/new_task")
        if date < current_date1:
            flash("Please enter a valid date.")
            return redirect("/new_task")
        db.execute("INSERT INTO plan (subject, task, due_to, original_due_to, user_id) VALUES (?, ?, ?, ?, ?)", subject, task, date, date, session["user_id"])
        flash("You successfully added a new task.")
        return redirect("/")
    else:
        return render_template("new_task.html", current_date=current_date1)

@app.route("/complete", methods=["POST"])
@login_required
def complete():
    task_id = request.form.get("task_id")
    db.execute("UPDATE plan SET is_completed = 1 WHERE id = ? AND user_id = ?", task_id, session["user_id"])
    return redirect("/")

@app.route("/my_tasks")
@login_required
def my_tasks():
    tasks = db.execute("SELECT * FROM plan WHERE user_id = ? ORDER BY due_to", session["user_id"])
    return render_template("my_tasks.html", tasks=tasks)

@app.route("/edit_task", methods=["GET", "POST"])
@login_required
def edit_task():
    if request.method == "POST":
        task_id = request.form.get("task_id")
        task = db.execute("SELECT due_to, original_due_to FROM plan WHERE user_id = ? AND id = ?", session["user_id"], task_id)[0]
        new_subject = request.form.get("subject")
        new_task = request.form.get("task")
        new_date = request.form.get("date")
        if not new_subject or not new_task or not new_date:
            flash("Please fill in all the blanks.")
            return redirect("/my_tasks")
        if task["original_due_to"] > new_date:
            flash("Please enter a valid date.")
            return redirect("/my_tasks")
        new_is_completed = request.form.get("comp")
        db.execute("UPDATE plan SET subject = ?, task = ?, due_to = ?, is_completed = ? WHERE user_id = ? AND id = ?", new_subject, new_task, new_date, new_is_completed, session["user_id"], task_id )
        flash("You successfully edited your task.")
        return redirect("/my_tasks")
    else:
        task_id = request.args.get("id")
        rows = db.execute("SELECT id, subject, task, due_to, original_due_to, is_completed  FROM plan WHERE user_id = ? AND id = ?", session["user_id"], task_id)
        if not rows:
            flash("Task not found.")
            return redirect("/my_tasks")
        task = rows[0]
        return render_template("edit_task.html", task=task)

@app.route("/delete_task")
@login_required
def delete_task():
    task_id = request.args.get("id")
    task = db.execute("SELECT id FROM plan WHERE user_id = ? AND id = ?", session["user_id"], task_id)
    if not task:
        flash("Task not found.")
        return redirect("/my_tasks")
    db.execute("DELETE FROM plan WHERE user_id = ? AND id = ?", session["user_id"], task_id)
    flash("You successfully deleted a task.")
    return redirect("/my_tasks")

@app.route("/progress")
@login_required
def progress():
    total_tasks = db.execute("SELECT COUNT(task) AS total_tasks FROM plan WHERE user_id = ?", session["user_id"])[0]["total_tasks"]
    total_completed = db.execute("SELECT COUNT(task) AS total_completed FROM plan WHERE user_id = ? AND is_completed = 1", session["user_id"])[0]["total_completed"]
    try:
        percentage = int((total_completed / total_tasks) * 100)
    except ZeroDivisionError:
        percentage = 0
    daily_progress = db.execute("SELECT due_to, COUNT(*) AS total, SUM(is_completed) AS completed FROM plan WHERE user_id = ? GROUP BY due_to ORDER BY due_to", session["user_id"])
    return render_template("progress.html", daily_progress=daily_progress, total_tasks=total_tasks, total_completed=total_completed, percentage=percentage)

@app.route("/subjects")
@login_required
def subjects():
    tasks = db.execute("SELECT subject, COUNT(*) AS total, SUM(is_completed) AS completed FROM plan WHERE user_id = ? GROUP BY subject", session["user_id"])
    return render_template("subjects.html", tasks=tasks)

@app.route("/change", methods=["GET", "POST"])
@login_required
def change():
    if request.method == "POST":
        new_password = request.form.get("new_password")
        new_confirmation = request.form.get("new_confirmation")
        current_password = request.form.get("current_password")
        current_hash = db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])[0]["hash"]
        if not current_password or not new_password or not new_confirmation:
            flash("Current password and/or new password and/or confirmation is blank.")
            return redirect("/change")
        elif not check_password_hash(current_hash, current_password):
            flash("Current password is incorrect.")
            return redirect("/change")
        elif new_confirmation != new_password:
            flash("Your confirmation does not match your password.")
            return redirect("/change")
        new_hash = generate_password_hash(new_password)
        db.execute("UPDATE users SET hash = ? WHERE id = ?", new_hash, session["user_id"])
        flash("You successfully changed your password")
        return redirect("/")
    else:
        return render_template("change.html")
