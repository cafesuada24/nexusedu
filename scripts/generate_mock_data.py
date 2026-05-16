import os
import random
import time
from datetime import UTC, datetime

import pandas as pd
import numpy as np

from src.core.identifiers import generate_uuid

# Constants
NUM_STUDENTS = 50
NUM_ANOMALY_STUDENTS = 10
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

# Failure Profiles for Anomaly Students
# 1-5: Critical
# 6-10: Elevated
FAILURE_PROFILES = {
    0: 'extreme_peer_failure',  # Critical: Score < 15
    1: 'sudden_collapse',      # Critical: Drop 90 -> 20
    2: 'systemic_decline',     # Critical: Drop in > 50% domains
    3: 'zero_activity',        # Critical: Score 0
    4: 'extreme_drift',        # Critical: Drop > 4.5 std dev
    5: 'gradual_trend',        # Elevated: Sustained negative drift
    6: 'moderate_drift',       # Elevated: Drop 80 -> 55
    7: 'moderate_peer_failure',# Elevated: Score ~45
    8: 'single_course_drop',   # Elevated: Significant failure in one domain
    9: 'sustained_low',        # Elevated: Borderline results
}

def generate_mock_data():
    # 1. Generate Students (SIS data)
    students = []
    for i in range(NUM_STUDENTS):
        sid = str(generate_uuid())
        name = f'Student {i}'
        
        # Determine if this student is an anomaly
        anomaly_profile = None
        if i < NUM_ANOMALY_STUDENTS:
            anomaly_profile = FAILURE_PROFILES[i]
            
        students.append(
            {
                'sid': sid,
                'student_name': name,
                'email': f'student_{i}@university.edu',
                'major': random.choice(MAJORS),
                'current_risk_status': 'Normal',
                'last_notified_timestamp': None,
                'last_notified_satisfaction': 0,
                'anomaly_profile': anomaly_profile, # Temporary
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
                        # 60% chance of an activity each week
                        if random.random() > 0.4:
                            base_score = 80.0 + random.normalvariate(0, 5)
                            
                            # Apply anomaly patterns in the last year, last semester, last 4 weeks
                            is_final_period = (year == 4 and semester == 2 and week >= 13)
                            profile = student['anomaly_profile']
                            
                            if is_final_period and profile:
                                if profile == 'extreme_peer_failure':
                                    base_score = random.uniform(5, 15)
                                elif profile == 'sudden_collapse':
                                    base_score = 20.0 + random.uniform(-5, 5)
                                elif profile == 'systemic_decline':
                                    base_score = 55.0 + random.uniform(-5, 5) # Multi-domain drop
                                elif profile == 'zero_activity':
                                    base_score = 0.0
                                elif profile == 'extreme_drift':
                                    base_score = 30.0 # From 80 to 30 is ~5 std devs if std=10
                                elif profile == 'gradual_trend':
                                    # Week 13: 70, Week 14: 65, Week 15: 60, Week 16: 55
                                    base_score = 85 - (week - 12) * 7.5
                                elif profile == 'moderate_drift':
                                    base_score = 55.0 + random.uniform(-5, 5)
                                elif profile == 'moderate_peer_failure':
                                    base_score = 45.0 + random.uniform(-5, 5)
                                elif profile == 'single_course_drop':
                                    # Only affect one course ID specifically
                                    if course['id'] == semester_courses[0]['id']:
                                        base_score = 30.0
                                elif profile == 'sustained_low':
                                    base_score = 65.0 + random.uniform(-5, 5)

                            final_score = max(0.0, min(100.0, float(base_score)))
                            activity_type = random.choice(TEST_TYPES)['type']

                            activities.append(
                                {
                                    'activity_id': str(generate_uuid()),
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
                                    ).isoformat(),
                                    'academic_year': year,
                                    'semester': semester,
                                    'week': week,
                                },
                            )

    # 3. Calculate Course Peer Statistics (avg and std)
    df_activities = pd.DataFrame(activities)
    
    # Group by academic_year, semester, week, and course_id to get stats
    stats = df_activities.groupby(['academic_year', 'semester', 'week', 'course_id'])['score'].agg(['mean', 'std']).reset_index()
    stats.columns = ['academic_year', 'semester', 'week', 'course_id', 'course_avg', 'course_std']
    
    # Fill NaN std (if only one student in a course/week) with a default
    stats['course_std'] = stats['course_std'].fillna(10.0)
    
    # Merge stats back to activities
    df_activities = df_activities.merge(stats, on=['academic_year', 'semester', 'week', 'course_id'], how='left')

    # Remove temporary 'anomaly_profile' from student records
    for s in students:
        if 'anomaly_profile' in s:
            del s['anomaly_profile']

    return students, df_activities


if __name__ == '__main__':
    students, df_activities = generate_mock_data()

    os.makedirs('data', exist_ok=True)

    # Save to individual files
    pd.DataFrame(students).to_csv('data/v2_students.csv', index=False)
    df_activities.to_csv('data/v2_activities.csv', index=False)

    print(f'Generated {len(students)} students.')
    print(f'Generated {len(df_activities)} activities.')
    print('Files saved to data/v2_students.csv and data/v2_activities.csv')
