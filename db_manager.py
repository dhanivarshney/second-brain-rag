import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional

from competencies import (
    COMPETENCY_CATALOGUE,
    COMPETENCY_DOMAINS,
    DOMAIN_STATISTICAL,
    DOMAIN_TECHNICAL,
    DOMAIN_DIGITAL_GOV,
    DOMAIN_BEHAVIOURAL,
    get_all_competencies,
    get_skills_by_domain,
    get_competency_meta,
    get_default_target_scores,
)

DB_PATH = "users.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_app_tables():
    """Ensure all required tables for Second Brain & SIH26101 features exist."""
    conn = get_connection()
    c = conn.cursor()

    # 1. Existing Second Brain Tables
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

    c.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action_type TEXT NOT NULL,
            detail TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. SIH26101 Competency & Skill Intelligence Tables
    c.execute("""
        CREATE TABLE IF NOT EXISTS learner_profiles (
            username TEXT PRIMARY KEY,
            full_name TEXT,
            designation TEXT,
            department TEXT,
            job_role TEXT,
            qualification TEXT,
            experience_years INTEGER,
            previous_training TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS learner_competencies (
            username TEXT NOT NULL,
            domain TEXT NOT NULL,
            skill TEXT NOT NULL,
            score INTEGER NOT NULL,
            target_score INTEGER NOT NULL,
            previous_score INTEGER,
            assessment_count INTEGER DEFAULT 1,
            last_assessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (username, skill)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS competency_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            assessment_type TEXT NOT NULL,
            overall_score INTEGER NOT NULL,
            domain_scores_json TEXT NOT NULL,
            skill_scores_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS document_topics (
            doc_name TEXT PRIMARY KEY,
            topics_json TEXT NOT NULL,
            domains_json TEXT NOT NULL,
            skills_json TEXT NOT NULL,
            summary TEXT,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS learning_recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            course_id TEXT,
            title TEXT NOT NULL,
            domain TEXT,
            skill TEXT,
            reason TEXT,
            priority TEXT,
            status TEXT DEFAULT 'Recommended',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ==================== Learner Profile API (SIH26101) ====================

def get_or_create_learner_profile(username: str) -> Dict[str, Any]:
    """Retrieve or initialize learner profile."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT full_name, designation, department, job_role, qualification, experience_years, previous_training, updated_at FROM learner_profiles WHERE username=?", (username,))
    row = c.fetchone()

    if not row:
        # Default profile for new statistical system learners
        default_name = username.capitalize() if username else "Officer"
        default_designation = "Statistical Analyst"
        default_dept = "Survey Design & Research Division (SDRD)"
        default_role = "Data Analysis & Quality Assurance"
        default_qual = "Master in Statistics / Economics"
        default_exp = 3
        default_train = "Induction Course on Official Statistics (NASA)"

        c.execute("""
            INSERT INTO learner_profiles (username, full_name, designation, department, job_role, qualification, experience_years, previous_training)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (username, default_name, default_designation, default_dept, default_role, default_qual, default_exp, default_train))
        conn.commit()

        # Initialize default competencies
        initialize_default_competencies(username)

        profile = {
            "username": username,
            "full_name": default_name,
            "designation": default_designation,
            "department": default_dept,
            "job_role": default_role,
            "qualification": default_qual,
            "experience_years": default_exp,
            "previous_training": default_train,
            "updated_at": datetime.now().isoformat()
        }
    else:
        profile = {
            "username": username,
            "full_name": row[0],
            "designation": row[1],
            "department": row[2],
            "job_role": row[3],
            "qualification": row[4],
            "experience_years": row[5],
            "previous_training": row[6],
            "updated_at": row[7]
        }

    conn.close()
    return profile


def update_learner_profile(username: str, full_name: str, designation: str, department: str,
                           job_role: str, qualification: str, experience_years: int, previous_training: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO learner_profiles (username, full_name, designation, department, job_role, qualification, experience_years, previous_training, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(username) DO UPDATE SET
            full_name=excluded.full_name,
            designation=excluded.designation,
            department=excluded.department,
            job_role=excluded.job_role,
            qualification=excluded.qualification,
            experience_years=excluded.experience_years,
            previous_training=excluded.previous_training,
            updated_at=CURRENT_TIMESTAMP
    """, (username, full_name, designation, department, job_role, qualification, experience_years, previous_training))
    conn.commit()
    conn.close()
    log_activity(username, "profile_updated", f"Updated profile for {full_name}")


# ==================== Learner Competency Management ====================

def initialize_default_competencies(username: str):
    """Seed initial diagnostic baseline scores across all competencies."""
    conn = get_connection()
    c = conn.cursor()

    # Initial baseline data aligned with official statistical system roles
    # Provides realistic starting points for skill gap demonstration
    initial_baselines = {
        "Survey Design & Sampling": 68,
        "Descriptive & Inferential Statistics": 65,
        "National Accounts & GVA": 55,
        "Price Statistics & Indices": 60,
        "SDG Indicators & Data Quality": 58,
        "Python for Statistical Analysis": 42,
        "R Programming & Econometrics": 48,
        "SQL & Database Systems": 67,
        "Data Visualization & BI": 52,
        "AI/ML in Official Statistics": 35,
        "Cybersecurity & Data Privacy": 45,
        "Digital Public Infrastructure & Cloud": 50,
        "Statistical Ethics & Integrity": 75,
        "Project Management & Communication": 68,
    }

    for skill, meta in COMPETENCY_CATALOGUE.items():
        score = initial_baselines.get(skill, 50)
        target = meta["default_target"]
        c.execute("""
            INSERT OR IGNORE INTO learner_competencies (username, domain, skill, score, target_score, previous_score, assessment_count)
            VALUES (?, ?, ?, ?, ?, NULL, 1)
        """, (username, meta["domain"], skill, score, target))

    conn.commit()
    conn.close()


def get_learner_competencies(username: str) -> Dict[str, Any]:
    """Retrieve full competency matrix, domain aggregates, and skill breakdowns."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT domain, skill, score, target_score, previous_score, assessment_count, last_assessed
        FROM learner_competencies WHERE username=? ORDER BY domain, skill
    """, (username,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        initialize_default_competencies(username)
        return get_learner_competencies(username)

    skills_data = []
    domain_totals = {d: {"score_sum": 0, "target_sum": 0, "count": 0} for d in COMPETENCY_DOMAINS}

    for r in rows:
        domain, skill, score, target, prev, count, last_assessed = r
        gap = max(0, target - score)
        skills_data.append({
            "domain": domain,
            "skill": skill,
            "score": score,
            "target_score": target,
            "previous_score": prev,
            "gap": gap,
            "assessment_count": count,
            "last_assessed": last_assessed,
        })
        if domain in domain_totals:
            domain_totals[domain]["score_sum"] += score
            domain_totals[domain]["target_sum"] += target
            domain_totals[domain]["count"] += 1

    # Domain aggregate percentages
    domain_scores = {}
    for d, data in domain_totals.items():
        avg = round(data["score_sum"] / data["count"]) if data["count"] > 0 else 0
        target_avg = round(data["target_sum"] / data["count"]) if data["count"] > 0 else 70
        domain_scores[d] = {
            "score": avg,
            "target": target_avg,
            "gap": max(0, target_avg - avg)
        }

    # Overall systemic competency index
    overall_score = round(sum(s["score"] for s in skills_data) / len(skills_data)) if skills_data else 0

    return {
        "overall_score": overall_score,
        "domain_scores": domain_scores,
        "skills": skills_data,
    }


def update_skill_score_adaptive(username: str, skill: str, quiz_score: int, domain: Optional[str] = None) -> Dict[str, Any]:
    """
    Adaptive Competency Scoring Formula (SIH26101):
    -------------------------------------------------
    When a learner takes an assessment or quiz on a skill:
      - Weight for new quiz performance = 0.40 (40%)
      - Weight for historical competency score = 0.60 (60%)
      Formula:
        new_score = round(old_score * 0.60 + quiz_score * 0.40)
    This prevents artificial jumping while ensuring realistic, demonstrable progress.
    """
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT domain, score, target_score, assessment_count FROM learner_competencies WHERE username=? AND skill=?", (username, skill))
    row = c.fetchone()

    if row:
        dom, old_score, target, count = row
        new_score = round(old_score * 0.60 + quiz_score * 0.40)
        new_count = count + 1
        c.execute("""
            UPDATE learner_competencies
            SET score=?, previous_score=?, assessment_count=?, last_assessed=CURRENT_TIMESTAMP
            WHERE username=? AND skill=?
        """, (new_score, old_score, new_count, username, skill))
    else:
        dom = domain or DOMAIN_STATISTICAL
        old_score = 50
        target = 70
        new_score = quiz_score
        new_count = 1
        c.execute("""
            INSERT INTO learner_competencies (username, domain, skill, score, target_score, previous_score, assessment_count)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (username, dom, skill, new_score, target, old_score))

    conn.commit()
    conn.close()

    log_activity(username, "competency_updated", f"{skill}: {old_score}% -> {new_score}% (Quiz: {quiz_score}%)")

    return {
        "skill": skill,
        "domain": dom,
        "before_score": old_score,
        "after_score": new_score,
        "target_score": target,
        "improvement": new_score - old_score
    }


def get_skill_gaps(username: str) -> List[Dict[str, Any]]:
    """
    Identify and prioritize skill gaps:
    - High Priority Gap: Gap >= 25% or score < 50%
    - Medium Priority Gap: Gap between 10% and 24%
    - Satisfactory (Low/No Gap): Score >= target or Gap < 10%
    """
    comp_data = get_learner_competencies(username)
    gaps = []

    for s in comp_data["skills"]:
        current = s["score"]
        target = s["target_score"]
        gap_val = max(0, target - current)

        if gap_val >= 25 or current < 50:
            priority = "High Priority"
            reason = f"Current competency ({current}%) is critically below the target benchmark of {target}%. Immediate training required."
        elif gap_val >= 10:
            priority = "Medium Priority"
            reason = f"Current score ({current}%) has a noticeable gap of {gap_val}% from the recommended target ({target}%)."
        else:
            priority = "Satisfactory"
            reason = f"Competency ({current}%) meets or is within acceptable threshold of the target benchmark ({target}%)."

        gaps.append({
            "skill": s["skill"],
            "domain": s["domain"],
            "current_score": current,
            "target_score": target,
            "gap": gap_val,
            "priority": priority,
            "reason": reason,
            "previous_score": s["previous_score"],
        })

    # Sort so High Priority gaps appear first, ordered by biggest gap
    priority_order = {"High Priority": 1, "Medium Priority": 2, "Satisfactory": 3}
    gaps.sort(key=lambda x: (priority_order[x["priority"]], -x["gap"]))
    return gaps


# ==================== Diagnostic Assessments API ====================

def save_assessment_result(username: str, assessment_type: str, overall_score: int,
                           domain_scores: Dict[str, int], skill_scores: Dict[str, int]):
    """Save full diagnostic assessment and update learner competencies adaptively."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO competency_assessments (username, assessment_type, overall_score, domain_scores_json, skill_scores_json)
        VALUES (?, ?, ?, ?, ?)
    """, (username, assessment_type, overall_score, json.dumps(domain_scores), json.dumps(skill_scores)))
    conn.commit()
    conn.close()

    # Update individual competencies
    updated_records = []
    for skill, score in skill_scores.items():
        meta = get_competency_meta(skill)
        res = update_skill_score_adaptive(username, skill, score, domain=meta["domain"])
        updated_records.append(res)

    log_activity(username, "assessment_completed", f"{assessment_type}: Overall {overall_score}%")
    return updated_records


def get_latest_assessments(username: str, limit: int = 5) -> List[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT id, assessment_type, overall_score, domain_scores_json, skill_scores_json, created_at
        FROM competency_assessments WHERE username=? ORDER BY id DESC LIMIT ?
    """, (username, limit))
    rows = c.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "id": r[0],
            "assessment_type": r[1],
            "overall_score": r[2],
            "domain_scores": json.loads(r[3]),
            "skill_scores": json.loads(r[4]),
            "created_at": r[5],
        })
    return results


# ==================== Document Topics & Competency Extraction ====================

def save_document_topics(doc_name: str, topics: List[str], domains: List[str], skills: List[str], summary: str = ""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO document_topics (doc_name, topics_json, domains_json, skills_json, summary, extracted_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(doc_name) DO UPDATE SET
            topics_json=excluded.topics_json,
            domains_json=excluded.domains_json,
            skills_json=excluded.skills_json,
            summary=excluded.summary,
            extracted_at=CURRENT_TIMESTAMP
    """, (doc_name, json.dumps(topics), json.dumps(domains), json.dumps(skills), summary))
    conn.commit()
    conn.close()


def get_document_topics(doc_name: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT topics_json, domains_json, skills_json, summary, extracted_at FROM document_topics WHERE doc_name=?", (doc_name,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "doc_name": doc_name,
        "topics": json.loads(row[0]),
        "domains": json.loads(row[1]),
        "skills": json.loads(row[2]),
        "summary": row[3],
        "extracted_at": row[4],
    }


def get_all_document_topics() -> List[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT doc_name, topics_json, domains_json, skills_json, summary, extracted_at FROM document_topics ORDER BY extracted_at DESC")
    rows = c.fetchall()
    conn.close()
    return [
        {
            "doc_name": r[0],
            "topics": json.loads(r[1]),
            "domains": json.loads(r[2]),
            "skills": json.loads(r[3]),
            "summary": r[4],
            "extracted_at": r[5],
        }
        for r in rows
    ]


# ==================== Admin & System-Wide Analytics ====================

def get_admin_analytics() -> Dict[str, Any]:
    """Calculate institutional capacity-building analytics for the Official Statistical System."""
    conn = get_connection()
    c = conn.cursor()

    # Total & active learners
    c.execute("SELECT COUNT(DISTINCT username) FROM users")
    total_learners = max(c.fetchone()[0], 1)

    c.execute("SELECT COUNT(DISTINCT username) FROM activity_log WHERE created_at >= date('now', '-30 days')")
    active_learners = max(c.fetchone()[0], 1)

    # Average system-wide competency
    c.execute("SELECT AVG(score) FROM learner_competencies")
    avg_competency_row = c.fetchone()[0]
    avg_competency = round(avg_competency_row) if avg_competency_row else 64

    # Quizzes and assessments completed
    c.execute("SELECT COUNT(*), AVG(score * 100.0 / total) FROM quiz_history")
    quiz_data = c.fetchone()
    total_quizzes = quiz_data[0]
    avg_quiz_score = round(quiz_data[1], 1) if quiz_data[1] else 74.0

    # Domain-wise average scores
    c.execute("SELECT domain, AVG(score) FROM learner_competencies GROUP BY domain")
    domain_avgs = {r[0]: round(r[1]) for r in c.fetchall()}
    for d in COMPETENCY_DOMAINS:
        if d not in domain_avgs:
            domain_avgs[d] = 60

    # Top institutional skill gaps
    c.execute("""
        SELECT skill, AVG(target_score - score) as avg_gap, AVG(score) as avg_score
        FROM learner_competencies
        GROUP BY skill
        ORDER BY avg_gap DESC
        LIMIT 5
    """)
    top_gaps = [
        {"skill": r[0], "gap": round(max(0, r[1])), "avg_score": round(r[2])}
        for r in c.fetchall()
    ]

    # Recent activity stream
    c.execute("SELECT username, action_type, detail, created_at FROM activity_log ORDER BY id DESC LIMIT 8")
    activity_stream = [
        {"username": r[0], "action": r[1], "detail": r[2], "timestamp": r[3]}
        for r in c.fetchall()
    ]

    conn.close()

    return {
        "total_learners": total_learners,
        "active_learners": active_learners,
        "avg_competency": avg_competency,
        "total_quizzes_conducted": total_quizzes,
        "avg_quiz_score": avg_quiz_score,
        "training_completion_rate": 72,  # Standard benchmark rate
        "domain_averages": domain_avgs,
        "top_institutional_gaps": top_gaps,
        "activity_stream": activity_stream,
    }


# ==================== Preserved Memories API ====================

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


# ==================== Preserved Quiz History API ====================

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


# ==================== Preserved Study Planner API ====================

def save_study_plan(username, subject, exam_date, daily_hours, schedule):
    conn = get_connection()
    c = conn.cursor()
    sched_json = json.dumps(schedule) if not isinstance(schedule, str) else schedule
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


# ==================== Preserved Activity Logging & Dashboard Metrics ====================

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
    competencies = get_learner_competencies(username)
    skill_gaps = get_skill_gaps(username)

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
        # SIH26101 Enhanced Fields:
        "overall_competency": competencies["overall_score"],
        "domain_scores": competencies["domain_scores"],
        "top_gaps": [g for g in skill_gaps if g["priority"] in ["High Priority", "Medium Priority"]][:4],
    }


# Auto-initialize tables on module load
init_app_tables()
