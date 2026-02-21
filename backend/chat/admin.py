from django.contrib import admin
from .models import (
    Conversation,
    Message,
    Contact,
    MessagesMedia,
)


class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "is_group",
        "created_at",
    )


class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "conversation",
        "sender",
        "reply_to",
        "created_at",
        "is_read",
    )


class ContactAdmin(admin.ModelAdmin):
    list_display = (
        "owner",
        "contact",
        "created_at",
    )


class MessagesMediaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "message",
        "file",
    )




admin.site.register(Conversation, ConversationAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(Contact, ContactAdmin)
admin.site.register(MessagesMedia, MessagesMediaAdmin)
