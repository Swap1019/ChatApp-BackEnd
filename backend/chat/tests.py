import pytest
from django.db import IntegrityError
from user.models import User
from chat.models import Conversations, Messages, Contacts

@pytest.fixture
def users(db):
    user1 = User.objects.create_user(username="user1", password="pass",email="kianjafari1386@gmail.com")
    user2 = User.objects.create_user(username="user2", password="pass",email="bitpinclient@gmail.com")
    return user1, user2

def test_conversation_creation(users):
    user1, user2 = users
    convo = Conversations.objects.create(is_group=False)
    convo.members.add(user1, user2)
    convo.save()

    assert convo.id is not None
    assert convo.members.count() == 2
    assert not convo.is_group

def test_message_creation(users):
    user1, user2 = users
    convo = Conversations.objects.create(is_group=False)
    convo.members.add(user1, user2)
    convo.save()

    msg = Messages.objects.create(
        conversation=convo,
        sender=user1,
        content="Hello",
    )

    assert msg.id is not None
    assert msg.conversation == convo
    assert msg.sender == user1
    assert msg.content == "Hello"
    assert not msg.is_read

def test_contacts_unique_constraint(users):
    user1, user2 = users

    contact1 = Contacts.objects.create(owner=user1, contact=user2)
    assert contact1.id is not None

    # Trying to create duplicate contact should raise IntegrityError
    with pytest.raises(IntegrityError):
        Contacts.objects.create(owner=user1, contact=user2)
