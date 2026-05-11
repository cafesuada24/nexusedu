import os
import random
import time
import uuid

import uuid6
from datetime import UTC, datetime, timedelta

import pandas as pd

# Constants
NUM_STUDENTS = 100
NUM_COURSES = 10
YEARS = [1, 2, 3, 4]
SEMESTERS = [1, 2]
WEEKS_PER_SEMESTER = 16

MAJORS = [
    'Computer Science',
    'Data Science',
    'Mathematics',
    'Physics',
    'Software Engineering',
]
COURSE_NAMES = [
    'Intro to Programming',
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

TEST_TYPES = [
    {'type': 'Quiz', 'weight': 0.1},
    {'type': 'Assignment', 'weight': 0.2},
    {'type': 'Midterm', 'weight': 0.3},
    {'type': 'Final', 'weight': 0.4},
]


def generate_mock_data():
    # 1. Generate Students (SIS data)
    students = []
    for i in range(NUM_STUDENTS):
        sid = uuid6.uuid7()
        name = f'Student {i}'
        profile = random.choices(
            ['steady', 'improving', 'degrading'], weights=[0.6, 0.2, 0.2],
        )[0]
        students.append(
            {
                'sid': str(sid),
                'student_name': name,
                'email': f'student_{i}@university.edu',
                'major': random.choice(MAJORS),
                'current_risk_status': 'Normal',
                'last_notified_timestamp': None,
                'last_notified_satisfaction': 0,
                'profile': profile,  # Temporary for score generation
            },
        )

    # 2. Generate Activities (LMS data)
    activities = []
    base_timestamp = int(time.time()) - (4 * 365 * 24 * 3600)  # Start 4 years ago

    courses = [
        {'id': f'C{100 + i}', 'name': name} for i, name in enumerate(COURSE_NAMES)
    ]

    for year in YEARS:
        for semester in SEMESTERS:
            # Advance time for each semester (~6 months)
            semester_offset = ((year - 1) * 2 + (semester - 1)) * (180 * 24 * 3600)

            for student in students:
                # Select 3-5 random courses per semester
                semester_courses = random.sample(courses, random.randint(3, 5))

                for course in semester_courses:
                    for week in range(1, WEEKS_PER_SEMESTER + 1):
                        # Not every week has a test
                        if random.random() > 0.4:  # 60% chance of an activity each week
                            # Determine base score based on profile and year
                            profile = student['profile']
                            if profile == 'degrading':
                                base_score = (
                                    90
                                    - (year * 10)
                                    - (week * 0.5)
                                    + random.randint(-5, 5)
                                )
                            elif profile == 'improving':
                                base_score = (
                                    60
                                    + (year * 8)
                                    + (week * 0.3)
                                    + random.randint(-5, 5)
                                )
                            else:
                                base_score = 75 + random.randint(-10, 10)

                            final_score = max(0.0, min(100.0, float(base_score)))

                            activity_type = random.choice(TEST_TYPES)['type']

                            activities.append(
                                {
                                    'activity_id': str(uuid6.uuid7()),
                                    'sid': student['sid'],
                                    'course_id': course['id'],
                                    'course_name': course['name'],
                                    'test_type': activity_type,
                                    'score': round(final_score, 2),
                                    'timestamp': datetime.fromtimestamp(
                                        base_timestamp
                                        + semester_offset
                                        + (week * 7 * 24 * 3600)
                                        + random.randint(0, 86400),
                                        tz=UTC,
                                    ),
                                    'academic_year': year,
                                    'semester': semester,
                                    'week': week,
                                },
                            )

    # Remove 'profile' from student records before saving
    for s in students:
        del s['profile']

    return students, activities


if __name__ == '__main__':
    students, activities = generate_mock_data()

    os.makedirs('data', exist_ok=True)

    # Save to individual files
    pd.DataFrame(students).to_csv('data/v2_students.csv', index=False)
    pd.DataFrame(activities).to_csv('data/v2_activities.csv', index=False)

    print(f'Generated {len(students)} students.')
    print(f'Generated {len(activities)} activities.')
    print('Files saved to data/v2_students.csv and data/v2_activities.csv')
