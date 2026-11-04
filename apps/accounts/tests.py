import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import User, UserProfile


def _png_bytes(size=(16, 16), color="blue"):
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


class UserModelTests(TestCase):
    def test_profile_created_on_user_creation(self):
        user = User.objects.create_user(email="a@example.com", password="pw-strong-123")
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

    def test_email_is_login_identifier(self):
        user = User.objects.create_user(email="b@example.com", password="pw-strong-123")
        self.assertEqual(user.USERNAME_FIELD, "email")
        self.assertEqual(str(user), "b@example.com")

    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="pw-strong-123")

    def test_superuser_flags(self):
        admin = User.objects.create_superuser(email="root@example.com", password="pw-strong-123")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)


class RegistrationTests(TestCase):
    def test_registration_creates_user_and_logs_in(self):
        resp = self.client.post(
            reverse("register"),
            {"email": "new@example.com", "password1": "pw-strong-123",
             "password2": "pw-strong-123"},
        )
        self.assertRedirects(resp, reverse("profile"))
        user = User.objects.get(email="new@example.com")
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        self.assertEqual(str(self.client.session["_auth_user_id"]), str(user.pk))

    def test_registration_rejects_mismatched_passwords(self):
        resp = self.client.post(
            reverse("register"),
            {"email": "x@example.com", "password1": "pw-strong-123",
             "password2": "different-456"},
        )
        self.assertEqual(resp.status_code, 200)  # re-render with errors
        self.assertFalse(User.objects.filter(email="x@example.com").exists())


class SessionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="u@example.com", password="pw-strong-123")

    def test_login_with_email(self):
        resp = self.client.post(
            reverse("login"), {"username": "u@example.com", "password": "pw-strong-123"}
        )
        self.assertRedirects(resp, reverse("profile"))

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        # GET is not allowed for logout in Django 5
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        resp = self.client.post(reverse("logout"))
        self.assertRedirects(resp, reverse("home"))


class ProfileAccessTests(TestCase):
    def setUp(self):
        self.a = User.objects.create_user(email="a@example.com", password="pw-strong-123")
        self.b = User.objects.create_user(email="b@example.com", password="pw-strong-123")

    def test_profile_requires_authentication(self):
        resp = self.client.get(reverse("member_detail", args=[self.a.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp.url)

    def test_authenticated_user_can_view_other_profile(self):
        self.client.force_login(self.b)
        resp = self.client.get(reverse("member_detail", args=[self.a.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "a@example.com")

    def test_user_cannot_edit_another_users_profile(self):
        # Structural: settings/ always edits request.user's own profile.
        self.client.force_login(self.b)
        self.client.post(reverse("settings"), {"full_name": "Intruder"})
        self.a.profile.refresh_from_db()
        self.b.profile.refresh_from_db()
        self.assertEqual(self.a.profile.full_name, "")        # A untouched
        self.assertEqual(self.b.profile.full_name, "Intruder")  # only B changed


class DeactivationTests(TestCase):
    def test_deactivation_blocks_future_login(self):
        user = User.objects.create_user(email="d@example.com", password="pw-strong-123")
        self.client.force_login(user)
        resp = self.client.post(reverse("deactivate"))
        self.assertRedirects(resp, reverse("home"))
        user.refresh_from_db()
        self.assertTrue(user.is_deactivated)
        self.assertFalse(user.is_active)
        # A deactivated (is_active=False) user can no longer authenticate.
        login_resp = self.client.post(
            reverse("login"), {"username": "d@example.com", "password": "pw-strong-123"}
        )
        self.assertEqual(login_resp.status_code, 200)  # re-render, not redirect
        self.assertNotIn("_auth_user_id", self.client.session)


class AvatarUploadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="av@example.com", password="pw-strong-123")
        self.client.force_login(self.user)
        self._media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self._media, ignore_errors=True)

    def test_valid_image_is_accepted(self):
        with override_settings(MEDIA_ROOT=self._media):
            img = SimpleUploadedFile("a.png", _png_bytes(), content_type="image/png")
            resp = self.client.post(reverse("settings"), {"avatar": img})
            self.assertRedirects(resp, reverse("profile"))
            self.user.profile.refresh_from_db()
            self.assertTrue(self.user.profile.avatar.name.startswith("avatars/"))

    def test_non_image_is_rejected(self):
        with override_settings(MEDIA_ROOT=self._media):
            bad = SimpleUploadedFile("a.txt", b"not an image", content_type="text/plain")
            resp = self.client.post(reverse("settings"), {"avatar": bad})
            self.assertEqual(resp.status_code, 200)  # re-render with errors
            self.user.profile.refresh_from_db()
            self.assertFalse(self.user.profile.avatar)
