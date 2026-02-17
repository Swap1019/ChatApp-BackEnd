def build_conversation_payload(conversation, viewer):
    """
    Build a conversation payload with a consistent shape for both private/group chats.
    """
    if conversation.is_group:
        return {
            "id": str(conversation.id),
            "name": conversation.name,
            "profile_url": conversation.profile_url,
            "is_group": True,
        }

    other_user = conversation.get_other_member(viewer)
    return {
        "id": str(conversation.id),
        "name": (other_user.nickname or other_user.username),
        "profile_url": other_user.profile_url,
        "is_group": False,
    }
