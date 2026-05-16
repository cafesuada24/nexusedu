"""Domain categorization logic for courses."""

from __future__ import annotations

from enum import StrEnum


class CourseDomain(StrEnum):
    """Broad academic domains for courses."""

    STEM = 'STEM'
    HUMANITIES = 'Humanities'
    SOCIAL_SCIENCES = 'Social Sciences'
    BUSINESS = 'Business'
    ARTS = 'Arts'
    OTHER = 'Other'


class DomainMapper:
    """Service to map course names/IDs to academic domains."""

    # Keywords for mapping
    KEYWORDS = {
        CourseDomain.STEM: [
            'programming',
            'data',
            'algorithm',
            'database',
            'system',
            'machine learning',
            'software',
            'network',
            'artificial intelligence',
            'cybersecurity',
            'math',
            'calculus',
            'physics',
            'chemistry',
            'biology',
            'engineering',
            'computer',
            'tech',
            'science',
        ],
        CourseDomain.HUMANITIES: [
            'philosophy',
            'history',
            'ethics',
            'literature',
            'art',
            'music',
            'religion',
            'language',
            'culture',
            'civilization',
        ],
        CourseDomain.SOCIAL_SCIENCES: [
            'sociology',
            'psychology',
            'political',
            'economics',
            'anthropology',
            'geography',
        ],
        CourseDomain.BUSINESS: [
            'management',
            'marketing',
            'finance',
            'accounting',
            'business',
            'entrepreneurship',
        ],
    }

    @classmethod
    def map(cls, course_name: str | None) -> CourseDomain:
        """Map a course name to a domain."""
        if not course_name:
            return CourseDomain.OTHER

        name_lower = course_name.lower()
        for domain, keywords in cls.KEYWORDS.items():
            if any(kw in name_lower for kw in keywords):
                return domain

        return CourseDomain.OTHER
