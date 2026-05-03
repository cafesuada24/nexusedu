"""Badge definitions for the advisor gamification system."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BadgeDefinition:
    """Immutable definition of an achievement badge."""

    badge_id: str
    name: str
    description: str
    icon: str  # Emoji or icon key for frontend rendering


# ── Badge Registry ──────────────────────────────────────────────
# Add new badges here. The GamificationService checks eligibility
# against this registry using advisor statistics.

BADGE_REGISTRY: dict[str, BadgeDefinition] = {
    'speed_demon': BadgeDefinition(
        badge_id='speed_demon',
        name='Speed Demon',
        description='Completed 3 actions within the 12-hour SLA window.',
        icon='⚡',
    ),
    'century_club': BadgeDefinition(
        badge_id='century_club',
        name='Century Club',
        description='Earned 100 total gamification points.',
        icon='💯',
    ),
    'five_hundred': BadgeDefinition(
        badge_id='five_hundred',
        name='Elite Advisor',
        description='Earned 500 total gamification points.',
        icon='🏆',
    ),
    'fastest_response': BadgeDefinition(
        badge_id='fastest_response',
        name='Fastest Responder',
        description='Maintained an average response time under 6 hours.',
        icon='🚀',
    ),
    'highest_recovery': BadgeDefinition(
        badge_id='highest_recovery',
        name='Recovery Champion',
        description='Achieved a student recovery rate above 80%.',
        icon='🌟',
    ),
}
