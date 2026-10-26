import sqlite3
import os
import json
from datetime import datetime, date, timedelta

DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'attendance.db')

def get_db_connection():
    """Returns a SQLite connection with row factory enabled and foreign keys enforced."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initializes the SQLite database tables if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Students Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            roll_number TEXT UNIQUE NOT NULL,
            class_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Attendance Table (UNIQUE constraint prevents duplicate entries for same student on same date)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Present', 'Absent')),
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            UNIQUE(student_id, attendance_date)
        )
    """)

    # 3. Engagement Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS engagement (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_date TEXT NOT NULL,
            activity_level TEXT NOT NULL CHECK(activity_level IN ('Low', 'Medium', 'High')),
            inactivity_minutes INTEGER NOT NULL,
            audio_activity TEXT NOT NULL CHECK(audio_activity IN ('Low', 'Medium', 'High')),
            engagement_score REAL NOT NULL,
            category TEXT NOT NULL,
            suggestions TEXT NOT NULL,
            session_notes TEXT DEFAULT ''
        )
    """)

    conn.commit()
    conn.close()

# -------------------------------------------------------------
# STUDENT OPERATIONS
# -------------------------------------------------------------

def get_all_students(search_query=None, class_filter=None):
    """Fetches all students, optionally filtered by search text or class."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM students WHERE 1=1"
    params = []

    if search_query:
        query += " AND (name LIKE ? OR roll_number LIKE ?)"
        term = f"%{search_query.strip()}%"
        params.extend([term, term])

    if class_filter:
        query += " AND class_name = ?"
        params.append(class_filter)

    query += " ORDER BY roll_number ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    students = [dict(r) for r in rows]
    conn.close()
    return students

def get_student_by_id(student_id):
    """Returns single student by primary key ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_student_by_roll(roll_number):
    """Returns single student by roll number."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE LOWER(roll_number) = LOWER(?)", (roll_number.strip(),))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_student(name, roll_number, class_name):
    """Adds a new student. Enforces uniqueness on roll number."""
    name = (name or "").strip()
    roll_number = (roll_number or "").strip().upper()
    class_name = (class_name or "").strip()

    if not name or not roll_number or not class_name:
        return False, "All fields (Name, Roll Number, Class) are required."

    if get_student_by_roll(roll_number):
        return False, f"Roll Number '{roll_number}' is already registered."

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO students (name, roll_number, class_name) VALUES (?, ?, ?)",
            (name, roll_number, class_name)
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return True, f"Student '{name}' ({roll_number}) added successfully."
    except sqlite3.IntegrityError:
        conn.close()
        return False, f"Roll Number '{roll_number}' already exists."
    except Exception as e:
        conn.close()
        return False, f"Database error: {str(e)}"

def update_student(student_id, name, roll_number, class_name):
    """Updates an existing student's details."""
    name = (name or "").strip()
    roll_number = (roll_number or "").strip().upper()
    class_name = (class_name or "").strip()

    if not name or not roll_number or not class_name:
        return False, "All fields are required."

    # Check duplicate roll number on other students
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM students WHERE LOWER(roll_number) = LOWER(?) AND id != ?",
        (roll_number, student_id)
    )
    if cursor.fetchone():
        conn.close()
        return False, f"Roll Number '{roll_number}' belongs to another student."

    try:
        cursor.execute(
            "UPDATE students SET name = ?, roll_number = ?, class_name = ? WHERE id = ?",
            (name, roll_number, class_name, student_id)
        )
        conn.commit()
        conn.close()
        return True, "Student updated successfully."
    except Exception as e:
        conn.close()
        return False, f"Database error: {str(e)}"

def delete_student(student_id):
    """Deletes student and cascade deletes their attendance records."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, roll_number FROM students WHERE id = ?", (student_id,))
    student = cursor.fetchone()
    if not student:
        conn.close()
        return False, "Student not found."

    cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    return True, f"Student '{student['name']}' deleted successfully."

def get_distinct_classes():
    """Returns list of distinct class names."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT class_name FROM students ORDER BY class_name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [r['class_name'] for r in rows]

# -------------------------------------------------------------
# ATTENDANCE OPERATIONS
# -------------------------------------------------------------

def get_attendance_for_date(attendance_date, class_filter=None):
    """
    Returns all registered students along with their attendance status
    for the specified date. Status is 'Present', 'Absent', or None if unmarked.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT 
            s.id AS student_id,
            s.name,
            s.roll_number,
            s.class_name,
            a.id AS attendance_id,
            a.status,
            a.attendance_date,
            a.updated_at
        FROM students s
        LEFT JOIN attendance a 
            ON s.id = a.student_id AND a.attendance_date = ?
        WHERE 1=1
    """
    params = [attendance_date]

    if class_filter:
        query += " AND s.class_name = ?"
        params.append(class_filter)

    query += " ORDER BY s.roll_number ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_bulk_attendance(attendance_date, records_dict):
    """
    Saves or updates attendance records for a given date.
    records_dict is a mapping of { student_id: 'Present' | 'Absent' }.
    Uses INSERT ... ON CONFLICT(student_id, attendance_date) DO UPDATE
    to prevent duplicate records.
    """
    if not attendance_date:
        return False, "Attendance date is required."

    if not records_dict:
        return False, "No attendance entries submitted."

    conn = get_db_connection()
    cursor = conn.cursor()
    saved_count = 0

    try:
        for student_id, status in records_dict.items():
            if status not in ('Present', 'Absent'):
                continue
            cursor.execute("""
                INSERT INTO attendance (student_id, attendance_date, status, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(student_id, attendance_date) DO UPDATE SET
                    status = excluded.status,
                    updated_at = CURRENT_TIMESTAMP
            """, (int(student_id), attendance_date, status))
            saved_count += 1

        conn.commit()
        conn.close()
        return True, f"Successfully recorded attendance for {saved_count} student(s) on {attendance_date}."
    except Exception as e:
        conn.rollback()
        conn.close()
        return False, f"Failed to save attendance: {str(e)}"

def get_attendance_stats_for_date(attendance_date):
    """Calculates total registered, present, absent, and percentage for a date."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total FROM students")
    total_students = cursor.fetchone()['total']

    cursor.execute("""
        SELECT 
            SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS present_count,
            SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END) AS absent_count,
            COUNT(*) AS total_marked
        FROM attendance
        WHERE attendance_date = ?
    """, (attendance_date,))
    row = cursor.fetchone()
    conn.close()

    present_count = row['present_count'] or 0
    absent_count = row['absent_count'] or 0
    total_marked = row['total_marked'] or 0

    percentage = round((present_count / total_students * 100), 1) if total_students > 0 else 0.0

    return {
        "date": attendance_date,
        "total_students": total_students,
        "present_count": present_count,
        "absent_count": absent_count,
        "total_marked": total_marked,
        "unmarked_count": max(0, total_students - total_marked),
        "percentage": percentage
    }

def get_latest_attendance_records(limit=10):
    """Returns the most recent individual attendance records."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            a.id,
            a.attendance_date,
            a.status,
            a.updated_at,
            s.name AS student_name,
            s.roll_number,
            s.class_name
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        ORDER BY a.attendance_date DESC, a.id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_student_attendance_summary():
    """
    Computes overall attendance statistics for each student.
    Returns list of dicts with present count, absent count, total sessions, and percentage.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            s.id AS student_id,
            s.name,
            s.roll_number,
            s.class_name,
            COUNT(a.id) AS total_sessions,
            SUM(CASE WHEN a.status = 'Present' THEN 1 ELSE 0 END) AS present_count,
            SUM(CASE WHEN a.status = 'Absent' THEN 1 ELSE 0 END) AS absent_count
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id
        GROUP BY s.id
        ORDER BY s.roll_number ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    summary = []
    for r in rows:
        item = dict(r)
        present = item['present_count'] or 0
        total = item['total_sessions'] or 0
        item['present_count'] = present
        item['absent_count'] = item['absent_count'] or 0
        item['percentage'] = round((present / total * 100), 1) if total > 0 else 0.0
        summary.append(item)
    return summary

def get_all_attendance_dates():
    """Returns distinct dates on which attendance has been recorded."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT attendance_date FROM attendance ORDER BY attendance_date DESC")
    rows = cursor.fetchall()
    conn.close()
    return [r['attendance_date'] for r in rows]

def get_all_attendance_records_for_export(date_filter=None):
    """Returns flat rows formatted for CSV export."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT 
            a.attendance_date,
            s.roll_number,
            s.name,
            s.class_name,
            a.status,
            a.updated_at
        FROM attendance a
        JOIN students s ON a.student_id = s.id
    """
    params = []
    if date_filter:
        query += " WHERE a.attendance_date = ?"
        params.append(date_filter)

    query += " ORDER BY a.attendance_date DESC, s.roll_number ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# -------------------------------------------------------------
# ENGAGEMENT & TEACHING SUGGESTIONS LOGIC
# -------------------------------------------------------------

def calculate_engagement_and_suggestions(activity_level, inactivity_minutes, audio_activity):
    """
    Transparent Python rule engine:
    1. Movement / Alertness (Low=12, Medium=28, High=40)
    2. Inactivity Duration (<=5m: 35, 6-15m: 25, 16-30m: 12, >30m: 2)
    3. Classroom Audio Activity (Low=8, Medium=18, High=25)
    Max = 40 + 35 + 25 = 100 pts.
    """
    try:
        inactivity_minutes = int(inactivity_minutes)
    except (ValueError, TypeError):
        inactivity_minutes = 0

    # 1. Activity score
    activity_map = {'High': 40, 'Medium': 28, 'Low': 12}
    activity_score = activity_map.get(activity_level, 20)

    # 2. Inactivity score
    if inactivity_minutes <= 5:
        inactivity_score = 35
    elif inactivity_minutes <= 15:
        inactivity_score = 25
    elif inactivity_minutes <= 30:
        inactivity_score = 12
    else:
        inactivity_score = 2

    # 3. Audio activity score
    audio_map = {'High': 25, 'Medium': 18, 'Low': 8}
    audio_score = audio_map.get(audio_activity, 15)

    raw_total = activity_score + inactivity_score + audio_score
    total_score = max(0, min(100, raw_total))

    # Category determination
    if total_score >= 75:
        category = "High Engagement"
        badge_color = "success"
        description = "Students exhibit high focus, active participation, and minimal classroom fatigue."
    elif total_score >= 50:
        category = "Moderate Engagement"
        badge_color = "warning"
        description = "Classroom attention is steady but showing signs of waning or passive listening."
    else:
        category = "Low Engagement"
        badge_color = "danger"
        description = "Classroom engagement is low. Fatigue, disinterest, or high inactivity detected."

    # Rule-Based Teaching Suggestions Generation
    suggestions = []
    rule_reasons = []

    if inactivity_minutes >= 20:
        suggestions.append("Prolonged Inactivity (>20 min): Pause the lecture monologue and ask quick concept questions or run a 'Think-Pair-Share' exercise.")
        rule_reasons.append(f"Inactivity is {inactivity_minutes} minutes, which exceeds the 20-minute threshold.")

    if audio_activity == 'Low':
        suggestions.append("Low Audio Activity: Initiate a 2-minute breakout discussion, ask for student volunteers to summarize the last point, or launch a quick poll.")
        rule_reasons.append("Audio activity is 'Low', indicating minimal vocal classroom participation.")

    if activity_level == 'Low':
        suggestions.append("Low Physical/Head Movement: Noticeable drowsiness or passive posture detected. Have students stand for a quick stretch or come to the board.")
        rule_reasons.append("Visual activity is 'Low', indicating static or fatigued students.")

    if total_score < 50:
        suggestions.append("Intervention Needed: Engagement score is below 50. Consider switching modalities (e.g., transition from slide presentation to live coding/problem-solving).")
        rule_reasons.append(f"Overall engagement score is {total_score}/100 (< 50).")

    if total_score >= 75 and audio_activity in ('Medium', 'High'):
        suggestions.append("Maintain Momentum: High engagement observed. Proceed with core curriculum, pose advanced challenge questions, or initiate peer review.")
        rule_reasons.append(f"High engagement score of {total_score}/100 with active audio dialogue.")

    if not suggestions:
        suggestions.append("Steady Classroom State: Proceed with scheduled lesson plan while periodically checking student comprehension.")
        rule_reasons.append("Indicators are in balanced moderate range.")

    return {
        "score": total_score,
        "category": category,
        "badge_color": badge_color,
        "description": description,
        "breakdown": {
            "activity_pts": activity_score,
            "inactivity_pts": inactivity_score,
            "audio_pts": audio_score,
            "max_pts": 100
        },
        "suggestions": suggestions,
        "rule_reasons": rule_reasons
    }

def save_engagement_session(session_date, activity_level, inactivity_minutes, audio_activity, session_notes=""):
    """Evaluates rules and persists an engagement session to the database."""
    calc = calculate_engagement_and_suggestions(activity_level, inactivity_minutes, audio_activity)
    suggestions_json = json.dumps(calc["suggestions"])

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO engagement (
            session_date, activity_level, inactivity_minutes, 
            audio_activity, engagement_score, category, suggestions, session_notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session_date,
        activity_level,
        int(inactivity_minutes),
        audio_activity,
        calc["score"],
        calc["category"],
        suggestions_json,
        session_notes.strip() if session_notes else ""
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    calc["id"] = new_id
    calc["session_date"] = session_date
    return calc

def get_recent_engagement_sessions(limit=10):
    """Fetches recent engagement sessions ordered by session_date DESC."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM engagement
        ORDER BY session_date DESC, id DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    sessions = []
    for r in rows:
        item = dict(r)
        try:
            item["suggestions_list"] = json.loads(item["suggestions"])
        except Exception:
            item["suggestions_list"] = [item["suggestions"]]
        sessions.append(item)
    return sessions

def get_all_engagement_sessions():
    """Fetches all engagement sessions for reports and trend charts."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM engagement ORDER BY session_date ASC, id ASC")
    rows = cursor.fetchall()
    conn.close()

    sessions = []
    for r in rows:
        item = dict(r)
        try:
            item["suggestions_list"] = json.loads(item["suggestions"])
        except Exception:
            item["suggestions_list"] = [item["suggestions"]]
        sessions.append(item)
    return sessions

# -------------------------------------------------------------
# SAMPLE DATA SEEDER
# -------------------------------------------------------------

def seed_sample_data():
    """Seeds realistic students, attendance history, and engagement sessions."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    sample_students = [
        ("Aarav Sharma", "CS201", "B.Tech CSE - Sec A"),
        ("Ananya Patel", "CS202", "B.Tech CSE - Sec A"),
        ("Rohan Verma", "CS203", "B.Tech CSE - Sec A"),
        ("Sneha Kulkarni", "CS204", "B.Tech CSE - Sec A"),
        ("Vikram Singh", "CS205", "B.Tech CSE - Sec A"),
        ("Priya Nair", "CS206", "B.Tech CSE - Sec B"),
        ("Aditya Gupta", "CS207", "B.Tech CSE - Sec B"),
        ("Neha Reddy", "CS208", "B.Tech CSE - Sec B"),
        ("Kavya Joshi", "CS209", "B.Tech CSE - Sec B"),
        ("Rahul Mehta", "CS210", "B.Tech CSE - Sec B"),
    ]

    for name, roll, class_name in sample_students:
        cursor.execute("""
            INSERT INTO students (name, roll_number, class_name)
            VALUES (?, ?, ?)
            ON CONFLICT(roll_number) DO UPDATE SET
                name = excluded.name,
                class_name = excluded.class_name
        """, (name, roll, class_name))
    conn.commit()

    # Get student IDs
    cursor.execute("SELECT id, roll_number FROM students ORDER BY roll_number")
    student_rows = cursor.fetchall()
    student_ids = [r['id'] for r in student_rows]

    # Generate attendance for the last 5 days
    today = date.today()
    dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(4, -1, -1)]

    # Realistic pattern of attendance
    patterns = [
        ['Present', 'Present', 'Present', 'Present', 'Present'],
        ['Present', 'Present', 'Absent', 'Present', 'Present'],
        ['Present', 'Absent', 'Present', 'Present', 'Absent'],
        ['Present', 'Present', 'Present', 'Present', 'Present'],
        ['Absent', 'Present', 'Present', 'Present', 'Present'],
        ['Present', 'Present', 'Present', 'Absent', 'Present'],
        ['Present', 'Present', 'Present', 'Present', 'Present'],
        ['Present', 'Absent', 'Present', 'Present', 'Present'],
        ['Absent', 'Absent', 'Present', 'Present', 'Present'],
        ['Present', 'Present', 'Present', 'Present', 'Present']
    ]

    for s_idx, s_id in enumerate(student_ids):
        p = patterns[s_idx % len(patterns)]
        for d_idx, d_str in enumerate(dates):
            status = p[d_idx]
            cursor.execute("""
                INSERT INTO attendance (student_id, attendance_date, status)
                VALUES (?, ?, ?)
                ON CONFLICT(student_id, attendance_date) DO UPDATE SET
                    status = excluded.status
            """, (s_id, d_str, status))
    conn.commit()

    # Seed engagement sessions for each of the dates
    sample_engagement = [
        (dates[0] + " 10:00:00", "High", 4, "High", "Morning Introductory Lecture"),
        (dates[1] + " 11:30:00", "Medium", 14, "Medium", "Data Structures Lab Overview"),
        (dates[2] + " 14:00:00", "Low", 26, "Low", "Post-lunch Theoretical Proofs"),
        (dates[3] + " 10:30:00", "Medium", 8, "High", "Interactive Algorithm Walkthrough"),
        (dates[4] + " 09:30:00", "High", 3, "Medium", "Review Session & Live Coding"),
    ]

    for s_date, act, inact, aud, notes in sample_engagement:
        # Check if already exists for exact date & time
        cursor.execute("SELECT id FROM engagement WHERE session_date = ?", (s_date,))
        if not cursor.fetchone():
            calc = calculate_engagement_and_suggestions(act, inact, aud)
            cursor.execute("""
                INSERT INTO engagement (
                    session_date, activity_level, inactivity_minutes,
                    audio_activity, engagement_score, category, suggestions, session_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                s_date, act, inact, aud, calc["score"], calc["category"],
                json.dumps(calc["suggestions"]), notes
            ))
    conn.commit()
    conn.close()
    return True
