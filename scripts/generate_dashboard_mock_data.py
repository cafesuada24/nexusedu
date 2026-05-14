import os
import uuid
import random
import pandas as pd
from datetime import datetime, timedelta, UTC
from src.core.identifiers import generate_uuid

# Constants
MAIN_ADVISOR_ID = '3a42d761-0e11-45c8-81bb-d0cde691fc5b' # Advisor 0
NUM_STUDENTS = 10
SEMESTERS = [
    {'year': 2025, 'sem': 1, 'name': 'Fall 2025', 'start': datetime(2025, 9, 1, tzinfo=UTC)},
    {'year': 2026, 'sem': 2, 'name': 'Spring 2026', 'start': datetime(2026, 2, 1, tzinfo=UTC)},
    {'year': 2026, 'sem': 1, 'name': 'Fall 2026', 'start': datetime(2026, 9, 1, tzinfo=UTC)},
]

# Student Profiles and Patterns
STUDENT_PROFILES = [
    {'name': 'Recovered Student', 'pattern': 'recovered'},
    {'name': 'Persistent Risk Student', 'pattern': 'persistent'},
    {'name': 'SLA Breach Student', 'pattern': 'breach'},
    {'name': 'No Activation Student', 'pattern': 'no_activation'},
    {'name': 'Activated Student', 'pattern': 'activated'},
    {'name': 'Current Critical Student', 'pattern': 'current_critical'},
    {'name': 'Current Elevated Student', 'pattern': 'current_elevated'},
    {'name': 'Normal Student A', 'pattern': 'normal'},
    {'name': 'Normal Student B', 'pattern': 'normal'},
    {'name': 'Normal Student C', 'pattern': 'normal'},
]

def generate_dashboard_data():
    students = []
    activities = []
    cases = []
    emails = []
    ledger = []
    appointments = []
    history = []

    # Prepare students
    for i, profile in enumerate(STUDENT_PROFILES):
        sid = generate_uuid()
        profile['sid'] = str(sid)
        students.append({
            'sid': str(sid),
            'student_name': profile['name'],
            'email': f'student_{i}@example.edu',
            'major': 'Computer Science',
            'current_risk_status': 'Normal',
            'last_notified_timestamp': None,
            'last_notified_satisfaction': 0
        })

    # Helper for points
    def add_points(advisor_id, case_id, action, points, earned_at):
        ledger.append({
            'id': str(generate_uuid()),
            'advisor_id': advisor_id,
            'case_id': case_id,
            'action': action,
            'points': points,
            'earned_at': earned_at.isoformat()
        })

    # Helper for case/email/engagement
    def create_intervention(sid, advisor_id, created_at, status, response_delay_hours=2, email_sent=True, engaged=False):
        case_id = str(generate_uuid())
        cases.append({
            'case_id': case_id,
            'sid': sid,
            'intervention_status': status,
            'created_at': created_at.isoformat(),
            'assigned_advisor_id': advisor_id,
            'version': 1,
            'closed_at': (created_at + timedelta(days=7)).isoformat() if status == 'resolved' else None
        })
        
        # Response action
        resp_at = created_at + timedelta(hours=response_delay_hours)
        add_points(advisor_id, case_id, 'first_response', 10, resp_at)

        if email_sent:
            email_id = str(generate_uuid())
            emails.append({
                'email_id': email_id,
                'case_id': case_id,
                'status': 'sent',
                'created_at': (created_at + timedelta(hours=response_delay_hours+1)).isoformat(),
                'sent_at': (created_at + timedelta(hours=response_delay_hours+2)).isoformat()
            })
            add_points(advisor_id, case_id, 'send_email', 5, created_at + timedelta(hours=response_delay_hours+2))

        if engaged:
            appt_id = str(generate_uuid())
            appt_time = created_at + timedelta(days=3)
            appointments.append({
                'appointment_id': appt_id,
                'case_id': case_id,
                'appointment_time': appt_time.isoformat(),
                'duration_minutes': 30,
                'meeting_method': 'in_person',
                'created_at': (created_at + timedelta(days=1)).isoformat()
            })
            add_points(advisor_id, case_id, 'book_appointment', 20, created_at + timedelta(days=1))
        
        if status == 'resolved':
            add_points(advisor_id, case_id, 'resolve_case', 50, created_at + timedelta(days=7))

        return case_id

    # Generate Semester Data
    for semester in SEMESTERS:
        y, s = semester['year'], semester['sem']
        sem_name = semester['name']
        sem_start = semester['start']

        for profile in STUDENT_PROFILES:
            sid = profile['sid']
            pattern = profile['pattern']
            
            # Determine Risk Status for this semester
            risk_status = 'Normal'
            if pattern == 'recovered' and sem_name == 'Fall 2025':
                risk_status = 'Critical'
            elif pattern == 'persistent':
                risk_status = 'Critical'
            elif pattern == 'breach' and sem_name == 'Fall 2025':
                risk_status = 'Elevated'
            elif pattern == 'no_activation' and sem_name == 'Fall 2025':
                risk_status = 'Elevated'
            elif pattern == 'activated' and sem_name == 'Fall 2025':
                risk_status = 'Elevated'
            elif pattern == 'current_critical' and sem_name == 'Spring 2026':
                risk_status = 'Critical'
            elif pattern == 'current_elevated' and sem_name == 'Spring 2026':
                risk_status = 'Elevated'

            # Update student's final status based on last "past/current" semester
            if sem_name in ['Fall 2025', 'Spring 2026']:
                for stu in students:
                    if stu['sid'] == sid:
                        stu['current_risk_status'] = risk_status

            # History
            history.append({
                'history_id': str(generate_uuid()),
                'sid': sid,
                'academic_year': y,
                'semester': s,
                'week': 8,
                'anomaly_flag': risk_status,
                'status_recorded_at': (sem_start + timedelta(weeks=8)).isoformat()
            })

            # Activities
            base_score = 80 if risk_status == 'Normal' else 40
            for w in range(1, 13):
                activities.append({
                    'activity_id': str(generate_uuid()),
                    'sid': sid,
                    'course_id': 'CS101',
                    'course_name': 'Intro to CS',
                    'test_type': 'Quiz',
                    'score': base_score + random.randint(-5, 10),
                    'timestamp': (sem_start + timedelta(weeks=w)).isoformat(),
                    'academic_year': y,
                    'semester': s,
                    'week': w
                })

            # Intervention logic (apply to past risk semesters)
            if risk_status != 'Normal' and sem_name in ['Fall 2025', 'Spring 2026']:
                created_at = sem_start + timedelta(weeks=8, days=1)
                
                if pattern == 'recovered':
                    create_intervention(sid, MAIN_ADVISOR_ID, created_at, 'resolved', engaged=True)
                elif pattern == 'persistent' and sem_name == 'Fall 2025':
                    create_intervention(sid, MAIN_ADVISOR_ID, created_at, 'supporting', engaged=True)
                elif pattern == 'breach':
                    create_intervention(sid, MAIN_ADVISOR_ID, created_at, 'accepted', response_delay_hours=48, email_sent=False)
                elif pattern == 'no_activation':
                    create_intervention(sid, MAIN_ADVISOR_ID, created_at, 'sent', email_sent=True, engaged=False)
                elif pattern == 'activated':
                    create_intervention(sid, MAIN_ADVISOR_ID, created_at, 'booked', email_sent=True, engaged=True)
                elif pattern == 'current_critical' and sem_name == 'Spring 2026':
                    cases.append({
                        'case_id': str(generate_uuid()),
                        'sid': sid,
                        'intervention_status': 'new',
                        'created_at': created_at.isoformat(),
                        'assigned_advisor_id': MAIN_ADVISOR_ID,
                        'version': 1
                    })
                elif pattern == 'current_elevated' and sem_name == 'Spring 2026':
                    cases.append({
                        'case_id': str(generate_uuid()),
                        'sid': sid,
                        'intervention_status': 'accepted',
                        'created_at': created_at.isoformat(),
                        'assigned_advisor_id': MAIN_ADVISOR_ID,
                        'version': 1
                    })

    # Save to CSV
    os.makedirs('data', exist_ok=True)
    pd.DataFrame(students).to_csv('data/v2_students.csv', index=False)
    pd.DataFrame(activities).to_csv('data/v2_activities.csv', index=False)
    pd.DataFrame(cases).to_csv('data/v2_cases.csv', index=False)
    pd.DataFrame(emails).to_csv('data/v2_intervention_emails.csv', index=False)
    pd.DataFrame(ledger).to_csv('data/v2_point_ledger.csv', index=False)
    pd.DataFrame(appointments).to_csv('data/v2_appointments.csv', index=False)
    pd.DataFrame(history).to_csv('data/v2_student_status_history.csv', index=False)

    print(f'Generated data for {NUM_STUDENTS} students across 3 semesters.')
    print('Files saved to data/v2_*.csv')

if __name__ == '__main__':
    generate_dashboard_data()
