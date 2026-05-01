from enum import Enum


class StudentSatisfaction(str, Enum):
    """Student statisfaction."""

    VERY_BAD = "very_bad"
    BAD = "bad"
    NORMAL = "normal"
    GOOD = "good"
    VERY_GOOD = "very_good"
