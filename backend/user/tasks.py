import os
from celery import shared_task
from cloudinary.uploader import upload
from .models import User

@shared_task
def upload_user_images(user_id, profile_path=None, background_path=None):
    user = User.objects.get(id=user_id)

    if profile_path:
        result = upload(profile_path)
        user.profile = result["secure_url"]
        os.remove(profile_path)

    if background_path:
        result = upload(background_path)
        user.background_image = result["secure_url"]
        os.remove(background_path)

    user.save()
    return {"status": "success"}
