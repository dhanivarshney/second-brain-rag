import json
import sqlite3
from datetime import datetime

DB_PATH = "users.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_app_tables():
    """Ensure all required tables for Second Brain features exist."""
    conn = get_connection()
    c = conn.cursor()

    # User memories (personal saved facts / notes)
    c.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Quiz history & weak areas
    c.execute("""
        CREATE TABLE IF NOT EXISTS quiz_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            topic TEXT,
            doc_source TEXT,
            score INTEGER,
            total INTEGER,
            weak_topics TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Study planner schedules
    c.execute("""
        CREATE TABLE IF NOT EXISTS study_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            subject TEXT,
            exam_date TEXT,
            daily_hours REAL,
            schedule_json TEXT,
            progress_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Activity tracking for Dashboard
    c.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action_type TEXT NOT NULL,
            detail TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ==================== Memories API ====================

def save_memory(username, content, title="", tags=""):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO memories (username, title, content, tags) VALUES (?, ?, ?, ?)",
        (username, title.strip() or "Note", content.strip(), tags.strip()),
    )
    conn.commit()
    mem_id = c.lastrowid
    conn.close()
    log_activity(username, "memory_saved", f"Saved note: {title or content[:30]}")
    return mem_id


def get_memories(username, search_query=""):
    conn = get_connection()
    c = conn.cursor()
    if search_query:
        param = f"%{search_query.strip()}%"
        c.execute(
            "SELECT id, title, content, tags, created_at FROM memories WHERE username=? AND (title LIKE ? OR content LIKE ? OR tags LIKE ?) ORDER BY id DESC",
            (username, param, param, param),
        )
    else:
        c.execute(
            "SELECT id, title, content, tags, created_at FROM memories WHERE username=? ORDER BY id DESC",
            (username,),
        )
    rows = c.fetchall()
    conn.close()
    return [
        {"id": r[0], "title": r[1], "content": r[2], "tags": r[3], "created_at": r[4]}
        for r in rows
    ]


def delete_memory(username, memory_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM memories WHERE id=? AND username=?", (memory_id, username))
    conn.commit()
    conn.close()


# ==================== Quiz History API ====================

def save_quiz_result(username, topic, doc_source, score, total, weak_topics):
    conn = get_connection()
    c = conn.cursor()
    weak_json = json.dumps(weak_topics) if isinstance(weak_topics, list) else str(weak_topics)
    c.execute(
        "INSERT INTO quiz_history (username, topic, doc_source, score, total, weak_topics) VALUES (?, ?, ?, ?, ?, ?)",
        (username, topic, doc_source, score, total, weak_json),
    )
    conn.commit()
    conn.close()
    log_activity(username, "quiz_completed", f"Quiz on {topic}: {score}/{total}")


def get_user_quiz_stats(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT score, total, weak_topics FROM quiz_history WHERE username=?", (username,))
    rows = c.fetchall()
    conn.close()

    total_quizzes = len(rows)
    total_score = sum(r[0] for r in rows)
    total_possible = sum(r[1] for r in rows)
    avg_score = round((total_score / total_possible * 100), 1) if total_possible > 0 else 0

    weak_counter = {}
    for r in rows:
        try:
            weaks = json.loads(r[2]) if r[2] else []
            for w in weaks:
                w_clean = w.strip()
                if w_clean:
                    weak_counter[w_clean] = weak_counter.get(w_clean, 0) + 1
        except Exception:
            pass

    sorted_weaks = sorted(weak_counter.items(), key=lambda x: x[1], reverse=True)
    return {
        "total_quizzes": total_quizzes,
        "avg_score": avg_score,
        "weak_topics": [topic for topic, _ in sorted_weaks[:8]],
    }


# ==================== Study Planner API ====================

def save_study_plan(username, subject, exam_date, daily_hours, schedule):
    conn = get_connection()
    c = conn.cursor()
    sched_json = json.dumps(schedule) if not isinstance(schedule, str) else schedule
    # Initialize all tasks unchecked
    progress = {str(i): False for i in range(len(schedule))} if isinstance(schedule, list) else {}
    prog_json = json.dumps(progress)
    c.execute(
        "INSERT INTO study_plans (username, subject, exam_date, daily_hours, schedule_json, progress_json) VALUES (?, ?, ?, ?, ?, ?)",
        (username, subject, str(exam_date), daily_hours, sched_json, prog_json),
    )
    conn.commit()
    plan_id = c.lastrowid
    conn.close()
    log_activity(username, "study_plan_created", f"Created study plan for {subject}")
    return plan_id


def get_latest_study_plan(username):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, subject, exam_date, daily_hours, schedule_json, progress_json, created_at FROM study_plans WHERE username=? ORDER BY id DESC LIMIT 1",
        (username,),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    try:
        sched = json.loads(row[4])
    except Exception:
        sched = []
    try:
        prog = json.loads(row[5])
    except Exception:
        prog = {}
    return {
        "id": row[0],
        "subject": row[1],
        "exam_date": row[2],
        "daily_hours": row[3],
        "schedule": sched,
        "progress": prog,
        "created_at": row[6],
    }


def update_plan_progress(plan_id, progress_dict):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE study_plans SET progress_json=? WHERE id=?",
        (json.dumps(progress_dict), plan_id),
    )
    conn.commit()
    conn.close()


# ==================== Activity Logging ====================

def log_activity(username, action_type, detail=""):
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO activity_log (username, action_type, detail) VALUES (?, ?, ?)",
            (username, action_type, detail),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_dashboard_metrics(username):
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM memories WHERE username=?", (username,))
    saved_memories_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM activity_log WHERE username=? AND action_type='question_asked'", (username,))
    questions_asked = c.fetchone()[0]

    conn.close()

    quiz_stats = get_user_quiz_stats(username)
    latest_plan = get_latest_study_plan(username)

    study_progress = 0
    if latest_plan and latest_plan["schedule"]:
        total_tasks = len(latest_plan["schedule"])
        completed_tasks = sum(1 for v in latest_plan["progress"].values() if v)
        study_progress = round((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0

    return {
        "questions_asked": questions_asked,
        "quizzes_completed": quiz_stats["total_quizzes"],
        "avg_quiz_score": quiz_stats["avg_score"],
        "weak_topics": quiz_stats["weak_topics"],
        "saved_memories": saved_memories_count,
        "study_progress": study_progress,
        "active_plan": latest_plan,
    }


# Auto-initialize tables on module load
init_app_tables()
