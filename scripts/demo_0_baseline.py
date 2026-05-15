"""Step 0: Establish a healthy baseline for all students."""

import os
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.core.identifiers import generate_uuid  # noqa: E402

# Constants
ADVISOR_ID = '3a42d761-0e11-45c8-81bb-d0cde691fc5b'
MAJORS = ['Computer Science', 'Business Administration', 'Mechanical Engineering', 'Digital Arts']
NUM_STUDENTS = 20

def generate_baseline() -> None:
    """Generate baseline CSV data with healthy students."""
    print("Generating baseline data (Weeks 1-4, all students healthy)...")

    students = []
    activities = []

    # Generate 20 healthy students
    for i in range(NUM_STUDENTS):
        sid = str(generate_uuid())
        major = MAJORS[i % len(MAJORS)]

        students.append({
            'sid': sid,
            'student_name': f'Student {chr(65+i)}',
            'email': f'student_{i}@example.edu',
            'major': major,
            'current_risk_status': 'Normal',
            'last_notified_timestamp': None,
            'last_notified_satisfaction': 0,
            'cumulative_gpa': 3.5,
        })

        # Healthy scores for weeks 1-4
        start_date = datetime(2026, 1, 5, tzinfo=UTC)
        for week in range(1, 5):
            activities.append({
                'activity_id': str(generate_uuid()),
                'sid': sid,
                'course_id': 'CS101' if i % 2 == 0 else 'BUS101',
                'course_name': 'Intro Course',
                'test_type': 'Quiz',
                'score': random.randint(80, 95),
                'timestamp': (start_date + timedelta(weeks=week-1)).isoformat(),
                'academic_year': 2026,
                'semester': 1,
                'week': week,
            })

    # Save to CSV
    os.makedirs('data', exist_ok=True)
    pd.DataFrame(students).to_csv('data/v2_students.csv', index=False)
    pd.DataFrame(activities).to_csv('data/v2_activities.csv', index=False)

    # Initialize other files as empty
    pd.DataFrame([{
        'advisor_id': ADVISOR_ID,
        'name': 'Demo Advisor',
        'email': 'adv@example.com',
        'title': 'Senior Advisor',
    }]).to_csv('data/v2_advisors.csv', index=False)

    pd.DataFrame([]).to_csv('data/v2_cases.csv', index=False)
    pd.DataFrame([]).to_csv('data/v2_intervention_emails.csv', index=False)
    pd.DataFrame([]).to_csv('data/v2_point_ledger.csv', index=False)
    pd.DataFrame([]).to_csv('data/v2_appointments.csv', index=False)
    pd.DataFrame([]).to_csv('data/v2_student_status_history.csv', index=False)

    print("\nBaseline CSVs generated.")
    print("NEXT STEP: Run 'uv run python scripts/reseed_all.py' to initialize the database.")

if __name__ == '__main__':
    generate_baseline()
