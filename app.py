from flask import Flask, request, jsonify, render_template
import re
import sqlite3
import os

app = Flask(__name__)

DB_PATH = "srms.db"

# ─── Database Setup ───────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT NOT NULL,
            roll    TEXT NOT NULL UNIQUE,
            course  TEXT NOT NULL,
            subject TEXT NOT NULL,
            marks   INTEGER NOT NULL,
            grade   TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# ─── Validation ───────────────────────────────────────────────────────
def is_valid_fullname(name):
    parts = name.strip().split()
    return len(parts) >= 2 and all(part.isalpha() for part in parts)

def is_valid_roll(roll):
    return bool(re.match(r'^[A-Za-z0-9]+$', str(roll).strip()))

def is_valid_course(course):
    return bool(course.strip()) and not course.strip().isdigit()

def is_valid_subject(subject):
    return bool(subject.strip()) and not subject.strip().isdigit()

def is_valid_marks(marks):
    return str(marks).isdigit() and 0 <= int(marks) <= 100

def get_grade(marks):
    if marks >= 90: return "A+"
    elif marks >= 75: return "A"
    elif marks >= 60: return "B"
    elif marks >= 45: return "C"
    elif marks >= 33: return "D"
    else: return "F"

# ─── Page ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

# ─── API: Add Student ─────────────────────────────────────────────────
@app.route("/api/add", methods=["POST"])
def add_student():
    data    = request.get_json()
    name    = data.get("name", "").strip()
    roll    = data.get("roll", "").strip().upper()
    course  = data.get("course", "").strip()
    subject = data.get("subject", "").strip()
    marks   = data.get("marks", "")

    if not is_valid_fullname(name):
        return jsonify({"success": False, "message": "Invalid name! First + Last name required."}), 400
    if not is_valid_roll(roll):
        return jsonify({"success": False, "message": "Invalid Roll! Alphanumeric only (e.g. 0537AL241109)."}), 400
    if not is_valid_course(course):
        return jsonify({"success": False, "message": "Invalid course!"}), 400
    if not is_valid_subject(subject):
        return jsonify({"success": False, "message": "Invalid subject!"}), 400
    if not is_valid_marks(str(marks)):
        return jsonify({"success": False, "message": "Invalid Marks! Must be 0–100."}), 400

    marks = int(marks)
    grade = get_grade(marks)

    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO students (name, roll, course, subject, marks, grade) VALUES (?,?,?,?,?,?)",
            (name.title(), roll, course.title(), subject.title(), marks, grade)
        )
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Student added successfully!"})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": f"Roll {roll} already exists!"}), 400

# ─── API: View All Students ───────────────────────────────────────────
@app.route("/api/students", methods=["GET"])
def view_students():
    conn     = get_db()
    rows     = conn.execute("SELECT * FROM students ORDER BY id").fetchall()
    conn.close()
    students = [dict(row) for row in rows]
    # Capitalize keys for frontend compatibility
    result = [{
        "Name":    s["name"],
        "Roll":    s["roll"],
        "Course":  s["course"],
        "Subject": s["subject"],
        "Marks":   s["marks"],
        "Grade":   s["grade"]
    } for s in students]
    return jsonify({"success": True, "students": result, "count": len(result)})

# ─── API: Search Student ──────────────────────────────────────────────
@app.route("/api/search", methods=["GET"])
def search_student():
    key = request.args.get("q", "").strip()
    if not key:
        return jsonify({"success": False, "message": "Empty search!"}), 400
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM students WHERE LOWER(name) LIKE ? OR UPPER(roll) LIKE ?",
        (f"%{key.lower()}%", f"%{key.upper()}%")
    ).fetchall()
    conn.close()
    if rows:
        result = [{"Name":r["name"],"Roll":r["roll"],"Course":r["course"],"Subject":r["subject"],"Marks":r["marks"],"Grade":r["grade"]} for r in rows]
        return jsonify({"success": True, "students": result})
    return jsonify({"success": False, "message": "No student found!"}), 404

# ─── API: Update Student ──────────────────────────────────────────────
@app.route("/api/update/<roll>", methods=["PUT"])
def update_student(roll):
    data    = request.get_json()
    course  = data.get("course", "").strip()
    subject = data.get("subject", "").strip()
    marks   = data.get("marks", "")

    if not is_valid_course(course):
        return jsonify({"success": False, "message": "Invalid course!"}), 400
    if not is_valid_subject(subject):
        return jsonify({"success": False, "message": "Invalid subject!"}), 400
    if not is_valid_marks(str(marks)):
        return jsonify({"success": False, "message": "Invalid Marks!"}), 400

    marks = int(marks)
    grade = get_grade(marks)

    conn = get_db()
    cur  = conn.execute(
        "UPDATE students SET course=?, subject=?, marks=?, grade=? WHERE UPPER(roll)=?",
        (course.title(), subject.title(), marks, grade, roll.upper())
    )
    conn.commit()
    conn.close()

    if cur.rowcount == 0:
        return jsonify({"success": False, "message": "Student not found!"}), 404
    return jsonify({"success": True, "message": "Student updated!"})

# ─── API: Delete Student ──────────────────────────────────────────────
@app.route("/api/delete/<roll>", methods=["DELETE"])
def delete_student(roll):
    conn = get_db()
    cur  = conn.execute("DELETE FROM students WHERE UPPER(roll)=?", (roll.upper(),))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        return jsonify({"success": False, "message": "Student not found!"}), 404
    return jsonify({"success": True, "message": f"Roll {roll} deleted!"})

# ─── Run ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    app.run(debug=True)