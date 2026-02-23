from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from user.models import User
from chat.models import Conversation


def _rewrite(url, target_base):
    if not url:
        return url
    if not isinstance(url, str):
        return url

    parsed = urlparse(url)
    if parsed.scheme in ("http", "https") and parsed.netloc in (
        "127.0.0.1:8000",
        "localhost:8000",
    ):
        return f"{target_base}{parsed.path}"
    if url.startswith("/media/"):
        return f"{target_base}{url}"
    return url


class Command(BaseCommand):
    help = "Rewrite stored localhost media URLs to MEDIA_PUBLIC_BASE_URL."

    def handle(self, *args, **options):
        base = settings.MEDIA_PUBLIC_BASE_URL
        if not base:
            raise CommandError(
                "MEDIA_PUBLIC_BASE_URL is empty. Set it in backend .env first."
            )

        user_count = 0
        group_count = 0

        for user in User.objects.all().iterator():
            changed_fields = []
            new_profile = _rewrite(user.profile, base)
            new_bg = _rewrite(user.background_image, base)
            if new_profile != user.profile:
                user.profile = new_profile
                changed_fields.append("profile")
            if new_bg != user.background_image:
                user.background_image = new_bg
                changed_fields.append("background_image")
            if changed_fields:
                user.save(update_fields=changed_fields)
                user_count += 1

        for conversation in Conversation.objects.filter(is_group=True).iterator():
            new_profile = _rewrite(conversation.profile, base)
            if new_profile != conversation.profile:
                conversation.profile = new_profile
                conversation.save(update_fields=["profile"])
                group_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Updated users={user_count}, groups={group_count}"
            )
        )
