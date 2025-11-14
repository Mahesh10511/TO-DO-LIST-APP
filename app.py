# app.py - Simple Flask To-Do List App
from flask import Flask, g, render_template, request, redirect, url_for, flash
import sqlite3
import os

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'todo.db')
SCHEMA = os.path.join(BASE_DIR, 'schema.sql')

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET', 'dev-secret')  # change before publishing


def get_db():
    db = getattr(g, '_db', None)
    if db is None:
        db = g._db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON;")
    return db


@app.teardown_appcontext
def close_db(e=None):
    db = getattr(g, '_db', None)
    if db is not None:
        db.close()


def init_db():
    if not os.path.exists(DB_PATH):
        with app.app_context():
            with open(SCHEMA, 'r') as f:
                get_db().executescript(f.read())
                get_db().commit()


@app.route('/')
def index():
    # optional filters
    show = request.args.get('show', 'all')  # all, active, completed
    sort = request.args.get('sort', 'created')  # created, due, priority
    q = "SELECT * FROM tasks"
    params = []
    if show == 'active':
        q += " WHERE completed = 0"
    elif show == 'completed':
        q += " WHERE completed = 1"
    if sort == 'due':
        q += " ORDER BY due_date IS NULL, due_date ASC"
    elif sort == 'priority':
        q += " ORDER BY priority ASC, created_at DESC"
    else:
        q += " ORDER BY created_at DESC"
    tasks = get_db().execute(q, params).fetchall()
    return render_template('index.html', tasks=tasks, show=show, sort=sort)


@app.route('/task/add', methods=['POST'])
def add_task():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    due_date = request.form.get('due_date') or None
    priority = int(request.form.get('priority') or 2)
    if not title:
        flash('Title is required.', 'warning')
        return redirect(url_for('index'))
    db = get_db()
    db.execute(
        "INSERT INTO tasks (title, description, due_date, priority) VALUES (?,?,?,?)",
        (title, description, due_date, priority)
    )
    db.commit()
    flash('Task added.', 'success')
    return redirect(url_for('index'))


@app.route('/task/<int:task_id>/toggle', methods=['POST'])
def toggle_task(task_id):
    db = get_db()
    cur = db.execute("SELECT completed FROM tasks WHERE id = ?", (task_id,))
    row = cur.fetchone()
    if not row:
        flash('Task not found.', 'danger')
        return redirect(url_for('index'))
    new = 0 if row['completed'] else 1
    db.execute("UPDATE tasks SET completed = ? WHERE id = ?", (new, task_id))
    db.commit()
    flash('Task updated.', 'success')
    return redirect(url_for('index'))


@app.route('/task/<int:task_id>/delete', methods=['POST'])
def delete_task(task_id):
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    flash('Task deleted.', 'info')
    return redirect(url_for('index'))


@app.route('/task/<int:task_id>/edit', methods=['GET', 'POST'])
def edit_task(task_id):
    db = get_db()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        due_date = request.form.get('due_date') or None
        priority = int(request.form.get('priority') or 2)
        if not title:
            flash('Title is required.', 'warning')
            return redirect(url_for('edit_task', task_id=task_id))
        db.execute("UPDATE tasks SET title=?, description=?, due_date=?, priority=? WHERE id=?",
                   (title, description, due_date, priority, task_id))
        db.commit()
        flash('Task saved.', 'success')
        return redirect(url_for('index'))
    task = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        flash('Task not found.', 'danger')
        return redirect(url_for('index'))
    return render_template('edit.html', task=task)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
