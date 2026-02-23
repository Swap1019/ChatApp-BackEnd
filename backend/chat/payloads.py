from .models import Message


def build_conversation_payload(conversation, viewer):
    """
    Build a conversation payload with a consistent shape for both private/group chats.
    """
    last_message = (
        Message.objects.filter(conversation=conversation)
        .select_related("sender")
        .order_by("-created_at")
        .first()
    )
    unread_count = Message.objects.filter(
        conversation=conversation, is_read=False
    ).exclude(sender=viewer).count()

    last_message_preview = None
    if last_message:
        sender_name = (
            last_message.sender.nickname
            if last_message.sender and last_message.sender.nickname
            else (
                last_message.sender.username
                if last_message.sender
                else "Unknown"
            )
        )
        last_message_preview = {
            "id": str(last_message.id),
            "content": last_message.content or "",
            "sender_nickname": sender_name,
            "created_at": last_message.created_at.isoformat(),
        }

    creator_id = str(conversation.created_by_id) if conversation.created_by_id else None
    viewer_is_creator = creator_id == str(viewer.id)
    viewer_is_admin = conversation.admins.filter(id=viewer.id).exists()

    if conversation.is_group:
        return {
            "id": str(conversation.id),
            "name": conversation.name,
            "profile_url": conversation.profile_url,
            "is_group": True,
            "created_by": creator_id,
            "viewer_is_creator": viewer_is_creator,
            "viewer_is_admin": viewer_is_admin,
            "unread_count": unread_count,
            "last_message": last_message_preview,
        }

    other_user = conversation.get_other_member(viewer)
    return {
        "id": str(conversation.id),
        "name": (other_user.nickname or other_user.username),
        "profile_url": other_user.profile_url,
        "is_group": False,
        "created_by": creator_id,
        "viewer_is_creator": viewer_is_creator,
        "viewer_is_admin": viewer_is_admin,
        "unread_count": unread_count,
        "last_message": last_message_preview,
    }
