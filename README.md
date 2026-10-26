# Multimodal Attendance & Engagement Agent

A lightweight, beginner-friendly classroom attendance management and engagement analytics web application built for college project evaluation and laboratory demonstrations.

---

## 📌 Project Overview

Traditional attendance systems only capture binary presence (*Present* or *Absent*), missing crucial insights into classroom attention and lecture effectiveness. The **Multimodal Attendance & Engagement Agent** bridges this gap:
1. **Attendance Tracking:** Simple roll-call management with SQLite persistence, preventing duplicate entries and calculating real-time attendance percentages.
2. **Engagement Analytics:** Simulates or logs multimodal classroom indicators (visual movement, continuous inactivity duration, acoustic participation) to compute an illustrative engagement score (0–100).
3. **Teaching Suggestions:** Generates actionable, transparent pedagogical interventions using deterministic Python rule-based logic.
4. **Offline & Privacy-First:** 100% local operation using SQLite, bundled local Chart.js, and zero cloud dependencies or biometric data storage.

---

## 🛠️ Technology Stack

- **Backend:** Python 3.10+ & Flask 3.x
- **Database:** SQLite3 (local persistent storage via `attendance.db`)
- **Frontend:** Semantic HTML5, CSS3 (Vanilla design system with modern slate/blue aesthetic), JavaScript (ES6)
- **Data Visualization:** Chart.js (bundled locally in `static/js/chart.umd.min.js` for full offline operation)
- **Computer Vision (Optional Demo):** OpenCV (`haarcascade_frontalface_default.xml`) for live head/presence detection
- **Reports:** Standard RFC 4180 CSV Export

---

## 📂 Project Architecture & Directory Structure

```text
attendance/
│
├── app.py                     # Main Flask web application, routing, and API endpoints
├── database.py                # SQLite database helper, schema definitions, rule scoring engine
├── requirements.txt           # Minimal Python dependencies (Flask, OpenCV)
├── attendance.db              # SQLite persistent database (auto-created on startup)
├── README.md                  # Complete Windows setup guide and viva presentation notes
│
├── templates/                 # Jinja2 HTML5 Templates
│   ├── base.html              # Core layout (sidebar, topbar, alert toasts, offline Chart.js)
│   ├── dashboard.html         # KPI metric cards, today's attendance, engagement trend chart
│   ├── students.html          # Student management (Add, Edit, Delete, Filter, Duplicate checks)
│   ├── attendance.html        # Date-wise roll-call sheet, bulk toggles, history preview
│   ├── engagement.html        # Interactive simulator, score gauge, points breakdown, trend chart
│   ├── teaching_suggestions.html # Rule engine transparency and pedagogical suggestions
│   ├── reports.html           # Cumulative student summary table, date reports, CSV exports
│   └── camera.html            # Optional OpenCV webcam presence demonstration
│
└── static/
    ├── css/
    │   └── style.css          # Clean, professional, responsive dashboard design system
    └── js/
        ├── app.js             # Client interactivity, attendance toggles, dynamic live calculations
        └── chart.umd.min.js   # Local bundled Chart.js library (enables 100% offline usage)
```

---

## 🚀 Step-by-Step Windows Setup Instructions

### Prerequisites
- Windows 10 or 11
- Python 3.10+ installed and added to `PATH` (Verify with `python --version`)

### Step 1: Open PowerShell or Command Prompt
Navigate to the project directory:
```powershell
cd c:\Users\HP\OneDrive\Desktop\attendance
```

### Step 2: (Optional but recommended) Create a Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*(If script execution is disabled in PowerShell, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Run the Application
```powershell
python app.py
```

### Step 5: Open in Web Browser
Open your browser and navigate to:
```text
http://127.0.0.1:5000
```

---

## 🎯 Key Implemented Features

### 1. Dashboard (`/dashboard`)
- **Key Performance Indicators (KPIs):** Total registered students, students present today, students absent today, today's attendance percentage bar.
- **Engagement Trend Chart:** Visualizes historical engagement scores across recent sessions.
- **Latest Attendance Table:** Live view of the most recent roll-call records.
- **Quick Action Bar:** Direct shortcuts to mark attendance, register students, simulate sessions, or export reports.

### 2. Student Management (`/students`)
- **Student Registration:** Add student with Name, Roll Number, and Class.
- **Validation:** Enforces mandatory fields and strictly prevents duplicate roll numbers.
- **Search & Filter:** Search by student name or roll number, and filter by class.
- **Edit & Delete Modals:** In-place editing and modal-confirmed deletion (with cascade removal of attendance history).
- **Cumulative Attendance Badge:** Displays individual student attendance rate percentage directly in the list.

### 3. Attendance Management (`/attendance`)
- **Date Picker:** Defaults to current date; allows selecting any past or future date.
- **Roll Call Sheet:** Clean Present/Absent status switches for each student.
- **Bulk Controls:** Single-click "Mark All Present" or "Mark All Absent".
- **Duplicate Prevention:** Uses SQLite `ON CONFLICT(student_id, attendance_date) DO UPDATE` to overwrite existing records without duplicate rows.
- **Real-Time Summary Bar:** Instant tally of present, absent, and percentage.
- **Date-Wise History Preview:** Quick button chips to jump to past attendance dates.
- **Date CSV Export:** One-click CSV download for the selected date.

### 4. Engagement Analytics & Simulator (`/engagement`)
- **Multimodal Indicator Inputs:**
  - *Visual/Head Movement Activity:* High (40 pts), Medium (28 pts), Low (12 pts)
  - *Inactivity Duration:* Slider from 0 to 60 minutes (<=5m: 35 pts, 6-15m: 25 pts, 16-30m: 12 pts, >30m: 2 pts)
  - *Audio Dialogue Activity:* High (25 pts), Medium (18 pts), Low (8 pts)
- **Live Calculation:** Dynamic recalculation via `/api/calculate-engagement` without full page reload.
- **Illustrative Score Gauge:** Displays total score (0–100) and category (*High Engagement*, *Moderate Engagement*, *Low Engagement*).
- **Session-over-Session Bar Chart:** Color-coded historical trends (Green for high, Amber for moderate, Red for low).
- **Persistent Storage:** Saves each session with optional topic notes into SQLite.

### 5. Teaching Suggestions (`/teaching-suggestions`)
- **Deterministic Rule Engine:** Transparently triggers pedagogical recommendations:
  - *Inactivity &ge; 20 mins:* Suggests questions, "Think-Pair-Share", or a brief pause.
  - *Low Audio Activity:* Recommends student breakout discussions or polls.
  - *Low Visual Movement:* Recommends a standing stretch or board-writing activity.
  - *Score < 50:* Triggers low engagement alert and suggests modality switch.
  - *Score &ge; 75 & Active Audio:* Recommends maintaining momentum and posing advanced challenge problems.
- **Viva Defense Transparency Box:** Shows the exact conditional logic and reasons that triggered each recommendation.

### 6. Reports & CSV Export (`/reports`)
- **Cumulative Student Attendance Summary:** Comprehensive table showing roll number, name, class, total sessions, present days, absent days, percentage %, and academic standing eligibility (&ge;75%).
- **Three One-Click CSV Exports:**
  1. `Download Attendance CSV` (`/reports/export/attendance`): Raw attendance logs.
  2. `Download Student Summary CSV` (`/reports/export/student-summary`): Cumulative attendance rates.
  3. `Download Engagement CSV` (`/reports/export/engagement`): All engagement sessions, scores, and suggestions.

### 7. Optional Camera Vision Demonstration (`/camera`)
- **Computer Vision Pipeline:** Uses OpenCV's built-in Haar Cascade classifier (`haarcascade_frontalface_default.xml`) to detect student presence and faces.
- **Bounding Box Overlay:** Draws live tracking rectangles and overlays a heads-up display (HUD).
- **Graceful Fallback:** If no webcam is plugged into the system, renders an informative test card and enables direct in-browser HTML5 webcam testing.
- **Privacy Notice:** Clearly explains that no biometric face templates are saved.

### 8. One-Click Demo Sample Data Seeder
- A button in the sidebar (**"⚡ Load Demo Sample Data"**) seeds 10 realistic students, 5 days of attendance history, and 5 engagement sessions for instant demonstration to examiners.

---

## 🧮 Engagement Scoring Formula (Viva Explanation)

The overall engagement score $S \in [0, 100]$ is computed as:
$$S = \text{ActivityScore} + \text{InactivityScore} + \text{AudioScore}$$

| Component | Indicator Values | Points Contribution |
|---|---|---|
| **Visual Head Movement** | High / Medium / Low | **40** / **28** / **12** points |
| **Inactivity Duration** | $\le 5$ min / $6-15$ min / $16-30$ min / $>30$ min | **35** / **25** / **12** / **2** points |
| **Classroom Audio** | High / Medium / Low | **25** / **18** / **8** points |
| **Total Maximum** | — | **100 points** |

### Engagement Categories:
- **$\ge 75$:** *High Engagement (Optimal Focus)* &mdash; Green
- **$50 - 74$:** *Moderate Engagement (Steady Focus)* &mdash; Amber
- **$< 50$:** *Low Engagement (Intervention Recommended)* &mdash; Red

---

## 🔒 Privacy & Offline Operation

- **100% Local Processing:** Runs on `localhost:5000` with SQLite storage.
- **No External Cloud APIs:** Does not transmit any student data or metrics over the internet.
- **Zero Biometric Harvesting:** OpenCV only estimates face counts and bounding boxes in volatile RAM; no facial vectors or personal biometrics are recorded in the database.
- **Bundled Assets:** Chart.js is bundled locally (`static/js/chart.umd.min.js`) so charts render without active internet connection.

---

## ⚠️ Known Limitations & Scope

1. **Simulated Indicators:** In this college project version, classroom multimodal indicators can be simulated or manually logged using sliders and selectors, unless linked with physical optical/acoustic sensors.
2. **Camera Modality:** The OpenCV camera feature demonstrates face presence and head movement detection; it does not perform automated per-student identification or facial recognition.
3. **Single-Teacher Architecture:** Built as a single-instructor classroom management console without complex multi-tenant role-based authentication.
