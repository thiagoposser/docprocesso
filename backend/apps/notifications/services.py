from collections.abc import Iterable

from django.contrib.auth.models import Group
from django.utils import timezone

from .models import Notification, NotificationLevel, NotificationType, validate_action_url


class NotificationService:
    """Single creation gateway; future channels can be added behind this API."""

    @staticmethod
    def create(
        *, user, title, message, type=NotificationType.SYSTEM,
        level=NotificationLevel.INFO, action_url="", expires_at=None,
        deduplication_key="",
    ):
        validate_action_url(action_url)
        return Notification.objects.create(
            user=user, title=title[:160], message=message[:500], type=type,
            level=level, action_url=action_url, expires_at=expires_at,
            deduplication_key=deduplication_key[:160],
        )

    @staticmethod
    def create_once(
        *, user, deduplication_key, title, message,
        type=NotificationType.SYSTEM, level=NotificationLevel.INFO,
        action_url="", expires_at=None,
    ):
        validate_action_url(action_url)
        notification, created = Notification.objects.get_or_create(
            user=user, deduplication_key=deduplication_key[:160],
            defaults={
                "title": title[:160], "message": message[:500], "type": type,
                "level": level, "action_url": action_url, "expires_at": expires_at,
            },
        )
        if not created and notification.expires_at and notification.expires_at <= timezone.now():
            notification.title = title[:160]
            notification.message = message[:500]
            notification.type = type
            notification.level = level
            notification.action_url = action_url
            notification.expires_at = expires_at
            notification.read = False
            notification.read_at = None
            notification.save(update_fields=(
                "title", "message", "type", "level", "action_url",
                "expires_at", "read", "read_at",
            ))
        return notification, created

    @classmethod
    def create_for_users(cls, users: Iterable, **kwargs):
        return [cls.create(user=user, **kwargs) for user in users if user.is_active]

    @classmethod
    def create_for_group(cls, group_name, *, exclude_user=None, **kwargs):
        group = Group.objects.filter(name=group_name).first()
        if not group:
            return []
        users = group.user_set.filter(is_active=True)
        if exclude_user:
            users = users.exclude(pk=exclude_user.pk)
        return cls.create_for_users(users, **kwargs)
