"""Configuration constants for the database layer."""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict

# Thư mục chứa các file .duckdb — resolve từ gốc project
DATA_DIR = 'data'

# ============================================================================
# DATABASE REGISTRY
# ============================================================================

class DBDescription(TypedDict):
    """Database description for DB_REGISTRY."""
    id: str
    description: str
    dialect: str
    keywords: list[str]

DB_REGISTRY: list[DBDescription] = [
    {
        'id': 'lms_db',
        'description': (
            'Learning Management System (LMS). '
            'Source for student academic performance and assessment activities.'
        ),
        'dialect': 'duckdb',
        'keywords': [
            'assessment score',
            'student performance',
            'activities',
            'quizzes',
            'academic year',
            'semester',
            'sid',
        ],
    },
    {
        'id': 'sis_db',
        'description': (
            'Student Information System (SIS). '
            'Source for administrative profiles and longitudinal risk history.'
        ),
        'dialect': 'duckdb',
        'keywords': [
            'student profile',
            'students',
            'risk status',
            'intervention status',
            'kanban state',
            'anomaly history',
            'nudge history',
            'sid',
        ],
    },
]
