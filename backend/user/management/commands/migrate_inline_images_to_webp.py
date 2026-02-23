import base64
import os
import uuid
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image, UnidentifiedImageError

from user.models import User
from chat.models import Conversation


def _data_url_to_webp_url(data_url, folder, prefix):
    if not isinstance(data_url, str) or not data_url.startswith("data:image/"):
        return None

    header, encoded = data_url.split(",", 1)
    if ";base64" not in header:
        return None

    raw = base64.b64decode(encoded)
    image = Image.open(BytesIO(raw))
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")

    output = BytesIO()
    image.save(output, format="WEBP", quality=82, method=6)
    output.seek(0)

    filename = f"{prefix}_{uuid.uuid4().hex}.webp"
    path = os.path.join(folder, filename)
    saved_path = default_storage.save(path, ContentFile(output.read()))
    return default_storage.url(saved_path)


class Command(BaseCommand):
    help = "Convert inline base64 profile/background/group images into saved WebP files."

    def handle(self, *args, **options):
        user_profile_count = 0
        user_bg_count = 0
        group_profile_count = 0

        with transaction.atomic():
            for user in User.objects.all().iterator():
                changed = False
                try:
                    if user.profile and str(user.profile).startswith("data:image/"):
                        new_url = _data_url_to_webp_url(
                            str(user.profile), "profiles", f"{user.id}_profile"
                        )
                        if new_url:
                            user.profile = new_url
                            user_profile_count += 1
                            changed = True

                    if user.background_image and str(user.background_image).startswith("data:image/"):
                        new_url = _data_url_to_webp_url(
                            str(user.background_image),
                            "backgrounds",
                            f"{user.id}_background",
                        )
                        if new_url:
                            user.background_image = new_url
                            user_bg_count += 1
                            changed = True
                except (ValueError, UnidentifiedImageError, OSError):
                    continue

                if changed:
                    user.save(update_fields=["profile", "background_image"])

            for conversation in Conversation.objects.filter(is_group=True).iterator():
                if not conversation.profile:
                    continue
                if not str(conversation.profile).startswith("data:image/"):
                    continue

                try:
                    new_url = _data_url_to_webp_url(
                        str(conversation.profile), "group_profiles", f"{conversation.id}_group"
                    )
                except (ValueError, UnidentifiedImageError, OSError):
                    continue

                if new_url:
                    conversation.profile = new_url
                    conversation.save(update_fields=["profile"])
                    group_profile_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Inline image migration completed. "
                f"user.profile={user_profile_count}, "
                f"user.background_image={user_bg_count}, "
                f"conversation.profile={group_profile_count}"
            )
        )
