from collections.abc import Iterable

from django.contrib.auth.models import Group

from .models import Notification, NotificationLevel, NotificationType, validate_action_url


class NotificationService:
    """Single creation gateway; future channels can be added behind this API."""

    @staticmethod
    def create(*, user, title, message, type=NotificationType.SYSTEM, level=NotificationLevel.INFO, action_url="", expires_at=None):
        validate_action_url(action_url)
        return Notification.objects.create(user=user, title=title[:160], message=message[:500], type=type, level=level, action_url=action_url, expires_at=expires_at)

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
