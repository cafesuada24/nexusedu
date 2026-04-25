import json
import os
import random
import time
import uuid
from datetime import datetime, timedelta

import pandas as pd

# Constants
NUM_STUDENTS = 50
NUM_COURSES = 10
YEARS = [1, 2, 3, 4]
SEMESTERS = [1, 2]
TEST_TYPES = [
    {'type': 'middle_semester', 'weight': 0.3},
    {'type': 'final_semester', 'weight': 0.7},
]

COURSE_NAMES = [
    'Intro to Computer Science',
    'Data Structures',
    'Algorithms',
    'Database Systems',
    'Operating Systems',
    'Machine Learning',
    'Software Engineering',
    'Computer Networks',
    'Artificial Intelligence',
    'Cybersecurity',
]


def generate_mock_data() -> pd.DataFrame:
    # 1. Setup Students
    students = []
    for i in range(NUM_STUDENTS):
        # Assign a performance profile
        # 0: Steady, 1: Improving, 2: Degrading
        profile = random.choices([0, 1, 2], weights=[0.6, 0.2, 0.2])[0]
        name = f'Student_{i + 1}'
        students.append(
            {
                'id': uuid.uuid4(),
                'name': name,
                'email': f'{name.lower()}@university.edu',
                'profile': profile,
            }
        )

    # 2. Setup Courses
    courses = [{'id': uuid.uuid4(), 'name': name} for name in COURSE_NAMES]

    mock_records = []
    base_timestamp = int(time.time()) - (4 * 365 * 24 * 3600)  # Start 4 years ago

    # 3. Generate Scores
    for year in YEARS:
        for semester in SEMESTERS:
            # Advance time for each semester (~6 months)
            semester_offset = ((year - 1) * 2 + (semester - 1)) * (180 * 24 * 3600)

            for student in students:
                # Select 3-5 random courses per semester
                semester_courses = random.sample(courses, random.randint(3, 5))

                for course in semester_courses:
                    for test in TEST_TYPES:
                        # Determine score based on profile and year
                        base_score = 75  # Default average

                        if student['profile'] == 2:  # Degrading
                            # Starts strong (85-95), drops by ~12 points each year
                            base_score = 90 - (year * 12) + random.randint(-5, 5)
                        elif student['profile'] == 1:  # Improving
                            # Starts low (60s), grows each year
                            base_score = 60 + (year * 8) + random.randint(-5, 5)
                        else:  # Steady
                            base_score = random.randint(70, 85)

                        # Clamp score between 0 and 100
                        final_score = max(0.0, min(100.0, float(base_score)))

                        # Alert metadata logic
                        # If score is very low, simulate that they might have been notified recently
                        notified = 0
                        satisfaction = 0
                        if final_score < 60 and year > 2:
                            notified = (
                                base_timestamp
                                + semester_offset
                                + random.randint(1000, 5000)
                            )
                            satisfaction = random.randint(1, 3)

                        record = {
                            'sid': str(student['id']),
                            'student_name': student['name'],
                            'course_id': str(course['id']),
                            'course_name': course['name'],
                            'test_type': test['type'],
                            'email': student['email'],
                            'last_notified_timestamp': notified,
                            'last_notified_satisfaction': satisfaction,
                            'score': round(final_score, 2),
                            'timestamp': base_timestamp
                            + semester_offset
                            + random.randint(0, 86400),
                            'academic_year': year,
                            'semester': semester,
                        }
                        mock_records.append(record)

    return pd.DataFrame(mock_records)


# Execute and Save
data = generate_mock_data()
os.makedirs('data', exist_ok=True)
data.to_csv('data/mock_student_scores.csv', index=False)

# Output snippet
print(f'Generated {len(data)} score records.')
print('Sample Record:', data.iloc[0,])

