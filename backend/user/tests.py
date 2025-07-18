from django.test import TestCase
from user.models import User


class UserTestCase(TestCase):
    def setUp(self):
        self.kian = User.objects.create(
            username="Swipy",
            first_name="Kian",
            last_name="Jafari",
            email="kianjafari1386@gmail.com",
        )
        self.dina = User.objects.create(
            username="xDinax",
            first_name="Dina",
            last_name="Jafari",
            email="dinajafari1388@gmail.com",
        )

    def test_users_identity_string(self):
        kian = User.objects.get(username="Swipy")
        dina = User.objects.get(username="xDinax")
        kian_str = f"The name: {kian.get_full_name()} , The username: {kian.username} , The email: {kian.email}"
        dina_str = f"The name: {dina.get_full_name()} , The username: {dina.username} , The email: {dina.email}"

        self.assertEqual(
            kian_str,
            "The name: Kian Jafari , The username: Swipy , The email: kianjafari1386@gmail.com",
        )
        self.assertEqual(
            dina_str,
            "The name: Dina Jafari , The username: xDinax , The email: dinajafari1388@gmail.com",
        )
