"""User personalization and hybrid recommendation signals."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.destination import Destination
from app.models.feedback import Feedback, FeedbackType
from app.models.trip import Trip
from app.models.user import User


@dataclass(frozen=True)
class PersonalizationProfile:
    """Deterministic user preference profile."""

    category_affinity: dict[str, float]
    rated_destination_ids: frozenset[int]
    interaction_count: int


def _category_value(destination: Destination) -> str:
    """Return a normalized destination category."""
    category = getattr(
        destination.category,
        "value",
        destination.category,
    )
    return str(category).strip().lower()


def build_user_profile(
    db: Session,
    user: User,
) -> PersonalizationProfile:
    """Build a preference profile from the user's first-party feedback."""

    feedbacks = db.scalars(
        select(Feedback).where(
            Feedback.user_id == user.id,
            Feedback.destination_id.is_not(None),
            Feedback.rating.is_not(None),
            Feedback.feedback_type == FeedbackType.RATING,
        )
    ).all()

    category_scores: dict[str, list[float]] = defaultdict(list)
    rated_destination_ids: set[int] = set()

    destination_ids = {
        int(feedback.destination_id)
        for feedback in feedbacks
        if feedback.destination_id is not None
    }

    if destination_ids:
        destinations = db.scalars(
            select(Destination).where(
                Destination.id.in_(destination_ids)
            )
        ).all()

        destination_by_id = {
            destination.id: destination
            for destination in destinations
        }

        for feedback in feedbacks:
            if feedback.destination_id is None or feedback.rating is None:
                continue

            destination = destination_by_id.get(
                feedback.destination_id
            )

            if destination is None:
                continue

            category = _category_value(destination)

            # Normalize 1-5 rating to 0-1 affinity.
            rating = max(1.0, min(5.0, float(feedback.rating)))
            affinity = (rating - 1.0) / 4.0

            category_scores[category].append(affinity)
            rated_destination_ids.add(feedback.destination_id)

    category_affinity = {
        category: round(
            sum(values) / len(values),
            4,
        )
        for category, values in category_scores.items()
        if values
    }

    return PersonalizationProfile(
        category_affinity=category_affinity,
        rated_destination_ids=frozenset(rated_destination_ids),
        interaction_count=len(feedbacks),
    )


def personalized_category_score(
    destination: Destination,
    profile: PersonalizationProfile,
) -> float:
    """Return a 0-100 score based on learned category affinity."""

    category = _category_value(destination)

    if not profile.category_affinity:
        return 50.0

    affinity = profile.category_affinity.get(category)

    if affinity is None:
        return 50.0

    return round(affinity * 100.0, 2)


def explicit_preference_score(
    destination: Destination,
    trip: Trip,
) -> float:
    """Return a 0-100 score for explicit trip category preferences."""

    preferences = trip.preferences or {}
    categories = preferences.get("categories")

    if not isinstance(categories, list):
        return 50.0

    requested = {
        str(category).strip().lower()
        for category in categories
        if category
    }

    if not requested:
        return 50.0

    return (
        100.0
        if _category_value(destination) in requested
        else 0.0
    )


def hybrid_personalization_score(
    destination: Destination,
    trip: Trip,
    profile: PersonalizationProfile,
) -> float:
    """Combine explicit and learned user preferences."""

    explicit = explicit_preference_score(
        destination,
        trip,
    )

    learned = personalized_category_score(
        destination,
        profile,
    )

    # Explicit trip intent is stronger than historical behavior.
    return round(
        explicit * 0.65 + learned * 0.35,
        2,
    )


def personalization_explanation(
    destination: Destination,
    trip: Trip,
    profile: PersonalizationProfile,
) -> str | None:
    """Explain the personalization contribution."""

    explicit = explicit_preference_score(
        destination,
        trip,
    )

    learned = personalized_category_score(
        destination,
        profile,
    )

    category = _category_value(destination)

    reasons: list[str] = []

    if explicit >= 100:
        reasons.append("matches your current interests")

    affinity = profile.category_affinity.get(category)

    if affinity is not None:
        if affinity >= 0.75:
            reasons.append("matches categories you have rated highly")
        elif affinity <= 0.35:
            reasons.append("has weaker historical preference affinity")

    if not reasons:
        return None

    return "Personalized because it " + ", ".join(reasons) + "."
