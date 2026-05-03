"""Value objects and definitions for Achievement Badges."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BadgeDefinition:
    """Defines an achievement badge."""

    badge_id: str
    name: str
    description: str
    icon: str


BADGE_REGISTRY = [
    BadgeDefinition(
        badge_id='speed_demon',
        name='Speed Demon',
        description='Take 3 actions within the 12-hour SLA window.',
        icon='⚡',
    ),
    BadgeDefinition(
        badge_id='century_club',
        name='Century Club',
        description='Earn a total of 100 gamification points.',
        icon='💯',
    ),
    BadgeDefinition(
        badge_id='five_hundred',
        name='Elite Advisor',
        description='Earn a total of 500 gamification points.',
        icon='👑',
    ),
    BadgeDefinition(
        badge_id='fastest_avg_response',
        name='Fast Responder',
        description='Maintain an average response time of under 4 hours (min 5 actions).',
        icon='🚀',
    ),
    BadgeDefinition(
        badge_id='highest_recovery_rate',
        name='Recovery Expert',
        description='Achieve a student recovery rate of over 80% (min 5 resolves).',
        icon='🛡️',
    ),
]

BADGE_MAP = {b.badge_id: b for b in BADGE_REGISTRY}
