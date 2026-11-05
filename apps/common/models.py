from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base adding self-managing created/updated timestamps.

    Every concrete model in SkillSwap should inherit from this.
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class RateLimitCounter(models.Model):
    """Backing store for the fixed-window rate limiter (``apps.common.ratelimit``).

    One row per (scope, ident, window_start) bucket. Increments are done with a
    single atomic ``UPDATE ... count = F('count') + 1`` statement — deliberately
    NOT Django's ``cache.incr()``, which is a non-atomic read-modify-write on the
    LocMem/DatabaseCache backends and would under-count under concurrency,
    letting callers slip past the limit. A DB counter updated with ``F()`` is
    atomic even on SQLite (single write statement, serialized by the write lock),
    so the limiter fails *closed*: under a race it over-counts at worst, never
    under-counts. See docs/BUSINESS_RULES.md (rate limiting / SQLite concurrency).
    """

    scope = models.CharField(max_length=64)
    ident = models.CharField(max_length=190)
    window_start = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["scope", "ident", "window_start"],
                name="uniq_ratelimit_bucket",
            ),
        ]
        indexes = [models.Index(fields=["window_start"])]

    def __str__(self):
        return f"{self.scope}:{self.ident}@{self.window_start:%Y-%m-%dT%H:%M}={self.count}"
