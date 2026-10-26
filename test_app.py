"""
Comprehensive Automated Test Suite for Multimodal Attendance & Engagement Agent
Tests all 11 requirements specified in Project Specification Section 8.
"""
import unittest
import json
import io
import csv
from app import app
import database

class AttendanceEngagementTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()

    def setUp(self):
        # Initialize and seed database for fresh test run
        database.init_db()
        database.seed_sample_data()

    # 1. Test Application Starts and Dashboard Loads
    def test_01_dashboard_loads(self):
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Classroom Overview & Analytics", response.data)
        self.assertIn(b"Total Registered", response.data)

    # 2. Test Student Management (Add, View, Edit, Delete)
    def test_02_student_lifecycle(self):
        # A. Add Student
        res = self.client.post('/students', data={
            'name': 'Test Student',
            'roll_number': 'TEST999',
            'class_name': 'Test Class'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"TEST999", res.data)
        self.assertIn(b"Test Student", res.data)

        # Verify in DB
        student = database.get_student_by_roll('TEST999')
        self.assertIsNotNone(student)
        student_id = student['id']

        # B. Edit Student
        res_edit = self.client.post(f'/students/edit/{student_id}', data={
            'name': 'Updated Test Student',
            'roll_number': 'TEST999',
            'class_name': 'Updated Class'
        }, follow_redirects=True)
        self.assertEqual(res_edit.status_code, 200)
        updated = database.get_student_by_id(student_id)
        self.assertEqual(updated['name'], 'Updated Test Student')
        self.assertEqual(updated['class_name'], 'Updated Class')

        # C. Delete Student
        res_del = self.client.post(f'/students/delete/{student_id}', follow_redirects=True)
        self.assertEqual(res_del.status_code, 200)
        self.assertIsNone(database.get_student_by_id(student_id))

    # 3. Test Duplicate Roll Numbers are Rejected
    def test_03_duplicate_roll_rejected(self):
        # CS201 already exists in sample data
        res = self.client.post('/students', data={
            'name': 'Duplicate Person',
            'roll_number': 'CS201',
            'class_name': 'B.Tech CSE - Sec A'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"already registered", res.data)

    # 4. Test Attendance Marking and Saving
    def test_04_attendance_marking_and_saving(self):
        test_date = '2026-10-27'
        students = database.get_all_students()
        self.assertGreater(len(students), 0)

        # Mark first student Present, second student Absent
        s1 = students[0]
        s2 = students[1]
        post_data = {
            'attendance_date': test_date,
            f'status_{s1["id"]}': 'Present',
            f'status_{s2["id"]}': 'Absent'
        }

        res = self.client.post('/attendance', data=post_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Successfully recorded attendance", res.data)

        # Verify in attendance table
        sheet = database.get_attendance_for_date(test_date)
        s1_row = next(r for r in sheet if r['student_id'] == s1['id'])
        s2_row = next(r for r in sheet if r['student_id'] == s2['id'])
        self.assertEqual(s1_row['status'], 'Present')
        self.assertEqual(s2_row['status'], 'Absent')

    # 5. Test Duplicate Attendance Prevention (Upsert on same student and date)
    def test_05_prevent_duplicate_attendance_per_date(self):
        test_date = '2026-10-28'
        student = database.get_all_students()[0]

        # First save: Mark Present
        database.save_bulk_attendance(test_date, {student['id']: 'Present'})
        # Second save: Change to Absent on same date
        database.save_bulk_attendance(test_date, {student['id']: 'Absent'})

        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM attendance WHERE student_id = ? AND attendance_date = ?", (student['id'], test_date))
        count = cursor.fetchone()['count']
        cursor.execute("SELECT status FROM attendance WHERE student_id = ? AND attendance_date = ?", (student['id'], test_date))
        status = cursor.fetchone()['status']
        conn.close()

        self.assertEqual(count, 1, "Duplicate row was created for same student and date!")
        self.assertEqual(status, 'Absent', "Status was not updated correctly!")

    # 6. Test Attendance Percentage Calculation
    def test_06_attendance_percentage_calculation(self):
        stats = database.get_attendance_stats_for_date('2026-10-26')
        self.assertIn('percentage', stats)
        self.assertGreaterEqual(stats['percentage'], 0.0)
        self.assertLessEqual(stats['percentage'], 100.0)

        # Check student summary calculations
        summary = database.get_student_attendance_summary()
        for s in summary:
            self.assertIn('percentage', s)
            self.assertEqual(s['total_sessions'], s['present_count'] + s['absent_count'])

    # 7. Test Engagement Score & Suggestions Rule Engine
    def test_07_engagement_rules_and_suggestions(self):
        # Case A: Optimal Engagement
        calc_high = database.calculate_engagement_and_suggestions('High', 3, 'High')
        self.assertGreaterEqual(calc_high['score'], 75)
        self.assertEqual(calc_high['category'], 'High Engagement')

        # Case B: Low Engagement / High Inactivity
        calc_low = database.calculate_engagement_and_suggestions('Low', 35, 'Low')
        self.assertLess(calc_low['score'], 50)
        self.assertEqual(calc_low['category'], 'Low Engagement')
        # Check suggestions
        sug_text = " ".join(calc_low['suggestions'])
        self.assertTrue(any("Inactivity" in s for s in calc_low['suggestions']))

        # Test API endpoint
        res_api = self.client.post('/api/calculate-engagement', json={
            'activity_level': 'Low',
            'inactivity_minutes': 25,
            'audio_activity': 'Low'
        })
        self.assertEqual(res_api.status_code, 200)
        data = res_api.get_json()
        self.assertEqual(data['category'], 'Low Engagement')

    # 8. Test CSV Export Endpoints
    def test_08_csv_exports(self):
        # A. Attendance records CSV
        res1 = self.client.get('/reports/export/attendance')
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(res1.headers['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn("Attendance Date", res1.data.decode('utf-8'))

        # B. Student summary CSV
        res2 = self.client.get('/reports/export/student-summary')
        self.assertEqual(res2.status_code, 200)
        self.assertIn("Attendance Percentage", res2.data.decode('utf-8'))

        # C. Engagement sessions CSV
        res3 = self.client.get('/reports/export/engagement')
        self.assertEqual(res3.status_code, 200)
        self.assertIn("Engagement Score", res3.data.decode('utf-8'))

    # 9. Test Invalid / Empty Input Graceful Handling
    def test_09_invalid_input_handling(self):
        # Empty student name
        success, msg = database.add_student("", "CS999", "B.Tech")
        self.assertFalse(success)
        self.assertIn("required", msg)

        # Empty roll number
        success, msg = database.add_student("Test Name", "", "B.Tech")
        self.assertFalse(success)

        # Invalid attendance date
        success, msg = database.save_bulk_attendance("", {1: 'Present'})
        self.assertFalse(success)

    # 10. Test Persistence across DB reconnections
    def test_10_database_persistence(self):
        # Write student
        database.add_student("Persist Student", "PER001", "Database Class")
        # Query again from a fresh connection
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE roll_number = 'PER001'")
        row = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row['name'], 'Persist Student')

if __name__ == '__main__':
    unittest.main()
