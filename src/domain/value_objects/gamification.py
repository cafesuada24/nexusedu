"""Gamification value object."""

from enum import StrEnum


class RankingType(StrEnum):
    """Period for leaderboard."""

    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    SEMESTER = 'semester'
    ALL_TIME = 'all_time'
