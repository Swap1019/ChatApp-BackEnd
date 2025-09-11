from django.contrib import admin
from .models import (
    Conversation,
    Message,
    Contact,
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
        "created_at",
        "is_read",
    )


class ContactAdmin(admin.ModelAdmin):
    list_display = (
        "owner",
        "contact",
        "created_at",
    )




admin.site.register(Conversation, ConversationAdmin)
admin.site.register(Message, MessageAdmin)
admin.site.register(Contact, ContactAdmin)
