import os
import io
import csv
import json
import time
from datetime import date, datetime
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, Response, send_file
)
import database

app = Flask(__name__)
app.secret_key = "attendance-engagement-secret-key-college-demo"

# Ensure database is created on startup
with app.app_context():
    database.init_db()

# Optional OpenCV import for camera demo
OPENCV_AVAILABLE = False
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

# -------------------------------------------------------------
# CONTEXT PROCESSOR (Inject current date, stats into templates)
# -------------------------------------------------------------
@app.context_processor
def inject_global_data():
    today_str = date.today().strftime('%Y-%m-%d')
    return {
        'today_str': today_str,
        'current_year': datetime.now().year,
        'opencv_available': OPENCV_AVAILABLE
    }

# -------------------------------------------------------------
# 1. DASHBOARD
# -------------------------------------------------------------
@app.route('/')
@app.route('/dashboard')
def dashboard():
    today_str = date.today().strftime('%Y-%m-%d')
    stats = database.get_attendance_stats_for_date(today_str)
    all_students = database.get_all_students()
    latest_attendance = database.get_latest_attendance_records(limit=8)
    recent_engagement = database.get_recent_engagement_sessions(limit=5)
    all_engagement = database.get_all_engagement_sessions()

    # Engagement summary
    avg_engagement = 0
    if all_engagement:
        avg_engagement = round(sum(s['engagement_score'] for s in all_engagement) / len(all_engagement), 1)

    latest_session = recent_engagement[0] if recent_engagement else None

    # Chart data for past engagement sessions
    chart_dates = [s['session_date'].split()[0] if ' ' in s['session_date'] else s['session_date'] for s in all_engagement[-7:]]
    chart_scores = [s['engagement_score'] for s in all_engagement[-7:]]

    return render_template(
        'dashboard.html',
        active_page='dashboard',
        stats=stats,
        total_students=len(all_students),
        latest_attendance=latest_attendance,
        recent_engagement=recent_engagement,
        avg_engagement=avg_engagement,
        latest_session=latest_session,
        chart_dates=json.dumps(chart_dates),
        chart_scores=json.dumps(chart_scores)
    )

# -------------------------------------------------------------
# 2. STUDENT MANAGEMENT
# -------------------------------------------------------------
@app.route('/students', methods=['GET', 'POST'])
def students():
    if request.method == 'POST':
        name = request.form.get('name')
        roll_number = request.form.get('roll_number')
        class_name = request.form.get('class_name')

        success, msg = database.add_student(name, roll_number, class_name)
        if success:
            flash(msg, 'success')
        else:
            flash(msg, 'danger')
        return redirect(url_for('students'))

    search = request.args.get('search', '').strip()
    class_filter = request.args.get('class_filter', '').strip()

    student_list = database.get_all_students(search_query=search, class_filter=class_filter)
    student_summaries = {s['student_id']: s for s in database.get_student_attendance_summary()}
    classes = database.get_distinct_classes()

    # Merge overall attendance stats into student list
    for s in student_list:
        summary = student_summaries.get(s['id'], {})
        s['present_count'] = summary.get('present_count', 0)
        s['absent_count'] = summary.get('absent_count', 0)
        s['total_sessions'] = summary.get('total_sessions', 0)
        s['percentage'] = summary.get('percentage', 0.0)

    return render_template(
        'students.html',
        active_page='students',
        students=student_list,
        classes=classes,
        search=search,
        selected_class=class_filter
    )

@app.route('/students/edit/<int:student_id>', methods=['POST'])
def edit_student(student_id):
    name = request.form.get('name')
    roll_number = request.form.get('roll_number')
    class_name = request.form.get('class_name')

    success, msg = database.update_student(student_id, name, roll_number, class_name)
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('students'))

@app.route('/students/delete/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    success, msg = database.delete_student(student_id)
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('students'))

# -------------------------------------------------------------
# 3. ATTENDANCE MANAGEMENT
# -------------------------------------------------------------
@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    today_str = date.today().strftime('%Y-%m-%d')
    selected_date = request.args.get('date', today_str).strip()
    selected_class = request.args.get('class_filter', '').strip()

    if request.method == 'POST':
        selected_date = request.form.get('attendance_date', today_str).strip()
        all_students = database.get_all_students()

        records = {}
        for s in all_students:
            val = request.form.get(f"status_{s['id']}")
            if val in ('Present', 'Absent'):
                records[s['id']] = val

        success, msg = database.save_bulk_attendance(selected_date, records)
        if success:
            flash(msg, 'success')
        else:
            flash(msg, 'danger')
        return redirect(url_for('attendance', date=selected_date, class_filter=selected_class))

    students_with_status = database.get_attendance_for_date(selected_date, class_filter=selected_class)
    stats = database.get_attendance_stats_for_date(selected_date)
    classes = database.get_distinct_classes()
    past_dates = database.get_all_attendance_dates()

    return render_template(
        'attendance.html',
        active_page='attendance',
        selected_date=selected_date,
        selected_class=selected_class,
        students=students_with_status,
        stats=stats,
        classes=classes,
        past_dates=past_dates
    )

# -------------------------------------------------------------
# 4. ENGAGEMENT ANALYTICS
# -------------------------------------------------------------
@app.route('/engagement', methods=['GET', 'POST'])
def engagement():
    today_dt = datetime.now().strftime('%Y-%m-%d %H:%M')

    if request.method == 'POST':
        session_date = request.form.get('session_date', today_dt)
        activity_level = request.form.get('activity_level', 'Medium')
        inactivity_minutes = request.form.get('inactivity_minutes', 10)
        audio_activity = request.form.get('audio_activity', 'Medium')
        session_notes = request.form.get('session_notes', '')

        result = database.save_engagement_session(
            session_date=session_date,
            activity_level=activity_level,
            inactivity_minutes=inactivity_minutes,
            audio_activity=audio_activity,
            session_notes=session_notes
        )
        flash(f"Engagement session recorded! Score: {result['score']}/100 ({result['category']})", 'success')
        return redirect(url_for('engagement'))

    recent_sessions = database.get_recent_engagement_sessions(limit=10)
    all_sessions = database.get_all_engagement_sessions()

    # Pre-calculate default preview
    default_preview = database.calculate_engagement_and_suggestions('Medium', 10, 'Medium')

    chart_dates = [s['session_date'].split()[0] if ' ' in s['session_date'] else s['session_date'] for s in all_sessions]
    chart_scores = [s['engagement_score'] for s in all_sessions]
    chart_notes = [s.get('session_notes') or s['category'] for s in all_sessions]

    return render_template(
        'engagement.html',
        active_page='engagement',
        recent_sessions=recent_sessions,
        default_preview=default_preview,
        today_dt=today_dt,
        chart_dates=json.dumps(chart_dates),
        chart_scores=json.dumps(chart_scores),
        chart_notes=json.dumps(chart_notes)
    )

@app.route('/api/calculate-engagement', methods=['POST'])
def api_calculate_engagement():
    """Live interactive calculation for frontend sliders/radios without reloading."""
    data = request.get_json() or {}
    activity_level = data.get('activity_level', 'Medium')
    inactivity_minutes = data.get('inactivity_minutes', 10)
    audio_activity = data.get('audio_activity', 'Medium')

    result = database.calculate_engagement_and_suggestions(
        activity_level, inactivity_minutes, audio_activity
    )
    return jsonify(result)

# -------------------------------------------------------------
# 5. TEACHING SUGGESTIONS
# -------------------------------------------------------------
@app.route('/teaching-suggestions')
def teaching_suggestions():
    session_id = request.args.get('session_id')
    recent_sessions = database.get_recent_engagement_sessions(limit=15)

    selected_session = None
    if session_id:
        for s in recent_sessions:
            if str(s['id']) == str(session_id):
                selected_session = s
                break

    if not selected_session and recent_sessions:
        selected_session = recent_sessions[0]

    # Recalculate to extract breakdown & transparent rule reasons
    breakdown_data = None
    if selected_session:
        breakdown_data = database.calculate_engagement_and_suggestions(
            selected_session['activity_level'],
            selected_session['inactivity_minutes'],
            selected_session['audio_activity']
        )

    return render_template(
        'teaching_suggestions.html',
        active_page='teaching_suggestions',
        selected_session=selected_session,
        recent_sessions=recent_sessions,
        breakdown_data=breakdown_data
    )

# -------------------------------------------------------------
# 6. REPORTS & CSV EXPORT
# -------------------------------------------------------------
@app.route('/reports')
def reports():
    student_summaries = database.get_student_attendance_summary()
    past_dates = database.get_all_attendance_dates()
    engagement_sessions = database.get_recent_engagement_sessions(limit=20)

    # Date-wise stats for the last 10 attendance dates
    date_summaries = []
    for d in past_dates[:10]:
        st = database.get_attendance_stats_for_date(d)
        date_summaries.append(st)

    return render_template(
        'reports.html',
        active_page='reports',
        student_summaries=student_summaries,
        date_summaries=date_summaries,
        engagement_sessions=engagement_sessions
    )

@app.route('/reports/export/attendance')
def export_attendance_csv():
    """Exports raw attendance records to CSV."""
    date_filter = request.args.get('date', '').strip() or None
    records = database.get_all_attendance_records_for_export(date_filter=date_filter)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Attendance Date", "Roll Number", "Student Name", "Class", "Status", "Recorded At"])

    for r in records:
        writer.writerow([
            r['attendance_date'],
            r['roll_number'],
            r['name'],
            r['class_name'],
            r['status'],
            r['updated_at']
        ])

    output.seek(0)
    filename = f"attendance_records_{date_filter if date_filter else 'all'}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.route('/reports/export/student-summary')
def export_student_summary_csv():
    """Exports student cumulative attendance summary to CSV."""
    summaries = database.get_student_attendance_summary()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Roll Number", "Student Name", "Class", "Total Sessions", "Present Days", "Absent Days", "Attendance Percentage"])

    for s in summaries:
        writer.writerow([
            s['roll_number'],
            s['name'],
            s['class_name'],
            s['total_sessions'],
            s['present_count'],
            s['absent_count'],
            f"{s['percentage']}%"
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=student_attendance_summary.csv"}
    )

@app.route('/reports/export/engagement')
def export_engagement_csv():
    """Exports engagement sessions to CSV."""
    sessions = database.get_all_engagement_sessions()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Session Date", "Activity Level", "Inactivity (Mins)",
        "Audio Activity", "Engagement Score", "Category", "Suggestions", "Notes"
    ])

    for s in sessions:
        sug_text = "; ".join(s['suggestions_list'])
        writer.writerow([
            s['session_date'],
            s['activity_level'],
            s['inactivity_minutes'],
            s['audio_activity'],
            s['engagement_score'],
            s['category'],
            sug_text,
            s.get('session_notes', '')
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=classroom_engagement_sessions.csv"}
    )

# -------------------------------------------------------------
# 7. OPTIONAL CAMERA FEATURE (Computer Vision Demonstration)
# -------------------------------------------------------------
@app.route('/camera')
def camera_demo():
    return render_template(
        'camera.html',
        active_page='camera',
        opencv_available=OPENCV_AVAILABLE
    )

def generate_video_frames():
    """
    Generator for OpenCV Haar cascade face detection video stream.
    Gracefully handles webcam unavailable by yielding informative placeholder frames.
    """
    if not OPENCV_AVAILABLE:
        return

    face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(face_cascade_path)

    # Attempt opening camera
    cap = cv2.VideoCapture(0)
    camera_opened = cap.isOpened()

    prev_face_count = 0

    try:
        while True:
            if camera_opened:
                success, frame = cap.read()
                if not success:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

                for (x, y, w, h) in faces:
                    # Draw bounding box
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (37, 99, 235), 2)
                    cv2.putText(
                        frame, "Classroom Head/Face", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (37, 99, 235), 2
                    )

                face_count = len(faces)
                status_text = f"Detected Faces: {face_count} | Sensor: Active"
                cv2.putText(
                    frame, status_text, (20, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (16, 185, 129), 2
                )

                ret, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
            else:
                # Synthetic simulated camera test card
                import numpy as np
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                frame[:] = (30, 25, 20)
                cv2.putText(frame, "Multimodal Camera Sensor (Demo Mode)", (40, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
                cv2.putText(frame, "Webcam device 0 not connected or busy.", (40, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (140, 140, 240), 2)
                cv2.putText(frame, "Use in-browser camera or manual indicators.", (40, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
                
                # Draw simulated classroom bounding box
                cv2.rectangle(frame, (200, 220), (440, 420), (37, 99, 235), 2)
                cv2.putText(frame, "Simulated Student Presence [OK]", (210, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (16, 185, 129), 2)
                
                ret, buffer = cv2.imencode('.jpg', frame)
                frame_bytes = buffer.tobytes()
                time.sleep(0.5)

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    finally:
        if camera_opened:
            cap.release()

@app.route('/api/video_feed')
def video_feed():
    if not OPENCV_AVAILABLE:
        return "OpenCV is not available", 503
    return Response(
        generate_video_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

# -------------------------------------------------------------
# 8. SEED SAMPLE DEMO DATA
# -------------------------------------------------------------
@app.route('/seed-demo-data', methods=['POST'])
def seed_demo():
    database.seed_sample_data()
    flash("Demo sample data successfully loaded! 10 students, 5 days of attendance, and engagement sessions are ready.", 'success')
    return redirect(request.referrer or url_for('dashboard'))

# -------------------------------------------------------------
# RUN APPLICATION
# -------------------------------------------------------------
if __name__ == '__main__':
    print("=" * 65)
    print("  Multimodal Attendance & Engagement Agent")
    print("  Running locally at: http://127.0.0.1:5000")
    print("  OpenCV status: " + ("Ready" if OPENCV_AVAILABLE else "Headless/Unavailable (Demo mode active)"))
    print("=" * 65)
    app.run(host='127.0.0.1', port=5000, debug=True)
