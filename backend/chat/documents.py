from django_elasticsearch_dsl import Document, Index, fields
from django_elasticsearch_dsl.registries import registry
from user.models import User


@registry.register_document
class UserDocument(Document):
    id = fields.KeywordField()
    username = fields.TextField()
    nickname = fields.TextField()
    profile_url = fields.TextField()

    class Index:
        name = "users"
        settings = {
            "number_of_shards": 3,
            "number_of_replicas": 2,
            "refresh_interval": "1s",
        }

    class Django:
        model = User
