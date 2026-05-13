from __future__ import annotations

import logging

from prometheus_client import REGISTRY
from prometheus_client.core import GaugeMetricFamily
from sqlalchemy import func

from . import cache
from .database import SessionLocal
from .models import DialogInitiation, Like, Match, Profile, Rating, Referral, Skip, User


logger = logging.getLogger(__name__)
_collector_registered = False


class DatingBotMetricsCollector:
    def collect(self):
        yield from self._collect_database_metrics()
        yield from self._collect_redis_metrics()

    def _collect_database_metrics(self):
        db = SessionLocal()
        try:
            users_total = db.query(func.count(User.id)).scalar() or 0
            profiles_total = db.query(func.count(Profile.id)).scalar() or 0
            profiles_with_photo = (
                db.query(func.count(Profile.id)).filter(Profile.photo_url.is_not(None)).scalar() or 0
            )
            likes_total = db.query(func.count(Like.id)).scalar() or 0
            skips_total = db.query(func.count(Skip.id)).scalar() or 0
            matches_total = db.query(func.count(Match.id)).scalar() or 0
            dialogs_total = db.query(func.count(DialogInitiation.id)).scalar() or 0
            referrals_total = db.query(func.count(Referral.id)).scalar() or 0

            yield GaugeMetricFamily(
                "dating_bot_users_total",
                "Total registered users.",
                value=users_total,
            )
            yield GaugeMetricFamily(
                "dating_bot_profiles_total",
                "Total created profiles.",
                value=profiles_total,
            )
            yield GaugeMetricFamily(
                "dating_bot_profiles_with_photo_total",
                "Profiles that have a photo stored in S3/MinIO.",
                value=profiles_with_photo,
            )
            yield GaugeMetricFamily("dating_bot_likes_total", "Total profile likes.", value=likes_total)
            yield GaugeMetricFamily("dating_bot_skips_total", "Total profile skips.", value=skips_total)
            yield GaugeMetricFamily("dating_bot_matches_total", "Total matches.", value=matches_total)
            yield GaugeMetricFamily(
                "dating_bot_dialogs_started_total",
                "Total dialog initiation events after matches.",
                value=dialogs_total,
            )
            yield GaugeMetricFamily(
                "dating_bot_referrals_total",
                "Total successful referral registrations.",
                value=referrals_total,
            )

            rating_count = db.query(func.count(Rating.user_id)).scalar() or 0
            averages = db.query(
                func.coalesce(func.avg(Rating.level1_score), 0.0),
                func.coalesce(func.avg(Rating.level2_score), 0.0),
                func.coalesce(func.avg(Rating.referral_score), 0.0),
                func.coalesce(func.avg(Rating.final_score), 0.0),
                func.coalesce(func.max(Rating.final_score), 0.0),
                func.coalesce(func.min(Rating.final_score), 0.0),
            ).one()

            yield GaugeMetricFamily("dating_bot_ratings_total", "Total rating rows.", value=rating_count)
            yield GaugeMetricFamily(
                "dating_bot_rating_level1_average",
                "Average Level 1 profile completeness score.",
                value=float(averages[0]),
            )
            yield GaugeMetricFamily(
                "dating_bot_rating_level2_average",
                "Average Level 2 behavioral score.",
                value=float(averages[1]),
            )
            yield GaugeMetricFamily(
                "dating_bot_rating_referral_average",
                "Average referral score.",
                value=float(averages[2]),
            )
            yield GaugeMetricFamily(
                "dating_bot_rating_final_average",
                "Average final combined rating.",
                value=float(averages[3]),
            )
            yield GaugeMetricFamily(
                "dating_bot_rating_final_max",
                "Maximum final combined rating.",
                value=float(averages[4]),
            )
            yield GaugeMetricFamily(
                "dating_bot_rating_final_min",
                "Minimum final combined rating.",
                value=float(averages[5]),
            )

            distribution = GaugeMetricFamily(
                "dating_bot_rating_distribution_users",
                "Number of users in final rating ranges.",
                labels=["range"],
            )
            for label, minimum, maximum in (
                ("0-20", 0, 20),
                ("20-40", 20, 40),
                ("40-60", 40, 60),
                ("60-80", 60, 80),
                ("80-100", 80, 101),
            ):
                count = (
                    db.query(func.count(Rating.user_id))
                    .filter(Rating.final_score >= minimum, Rating.final_score < maximum)
                    .scalar()
                    or 0
                )
                distribution.add_metric([label], count)
            yield distribution

            match_ratio = (matches_total / likes_total) if likes_total else 0.0
            profile_completion_ratio = (profiles_with_photo / profiles_total) if profiles_total else 0.0
            yield GaugeMetricFamily(
                "dating_bot_match_ratio",
                "Matches divided by total likes.",
                value=match_ratio,
            )
            yield GaugeMetricFamily(
                "dating_bot_profile_photo_completion_ratio",
                "Profiles with photos divided by total profiles.",
                value=profile_completion_ratio,
            )
            yield GaugeMetricFamily(
                "dating_bot_metrics_collection_success",
                "Whether database metrics collection succeeded.",
                value=1,
            )
        except Exception:
            logger.exception("prometheus.database_metrics_failed")
            yield GaugeMetricFamily(
                "dating_bot_metrics_collection_success",
                "Whether database metrics collection succeeded.",
                value=0,
            )
        finally:
            db.close()

    def _collect_redis_metrics(self):
        try:
            queue_lengths = [
                cache.redis_client.llen(key)
                for key in cache.redis_client.scan_iter("candidate_queue:*")
            ]
            queues_total = len(queue_lengths)
            average_length = sum(queue_lengths) / queues_total if queues_total else 0.0
            yield GaugeMetricFamily(
                "dating_bot_candidate_queues_total",
                "Total cached candidate queues in Redis.",
                value=queues_total,
            )
            yield GaugeMetricFamily(
                "dating_bot_candidate_queue_length_average",
                "Average cached candidate queue length.",
                value=average_length,
            )
            yield GaugeMetricFamily(
                "dating_bot_redis_metrics_collection_success",
                "Whether Redis metrics collection succeeded.",
                value=1,
            )
        except Exception:
            logger.exception("prometheus.redis_metrics_failed")
            yield GaugeMetricFamily(
                "dating_bot_redis_metrics_collection_success",
                "Whether Redis metrics collection succeeded.",
                value=0,
            )


def register_metrics_collector() -> None:
    global _collector_registered
    if _collector_registered:
        return
    REGISTRY.register(DatingBotMetricsCollector())
    _collector_registered = True
