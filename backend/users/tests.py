from __future__ import annotations

from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from base.models import Household
from finance.models import Category
from users.models import User
from users.services import password_link_url


class AccountRecoveryTests(APITestCase):
    def setUp(self) -> None:
        self.admin = User.objects.create_superuser(
            email="admin@example.test",
            password="Admin!Password2026",
            name="Admin",
        )
        self.user = User.objects.create_user(
            email="user@example.test",
            password="User!Password2026",
            name="User",
        )

    def test_login_error_is_a_clean_sentence(self) -> None:
        response = self.client.post(
            "/api/auth/login/",
            {"email": self.user.email, "password": "wrong"},
            format="json",
            HTTP_AUTHORIZATION="Token stale-client-token",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "E-Mail-Adresse oder Passwort ist falsch.")
        self.assertNotIn("ErrorDetail", response.data["detail"])

    def test_password_link_is_one_time_and_starts_a_new_session(self) -> None:
        token = self.user.issue_password_link(User.PasswordLinkPurpose.RESET)
        response = self.client.post(
            "/api/auth/password/reset/confirm/",
            {"token": token, "new_password": "Fresh!Password2027"},
            format="json",
            HTTP_AUTHORIZATION="Token stale-client-token",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["token"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Fresh!Password2027"))
        self.assertEqual(self.user.password_link_token_hash, "")

        reused = self.client.post(
            "/api/auth/password/reset/confirm/",
            {"token": token, "new_password": "Another!Password2028"},
            format="json",
        )
        self.assertEqual(reused.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("users.views.send_password_link")
    def test_password_reset_request_ignores_a_stale_client_token(self, send_link: Mock) -> None:
        response = self.client.post(
            "/api/auth/password/reset/request/",
            {"email": self.user.email},
            format="json",
            HTTP_AUTHORIZATION="Token stale-client-token",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        send_link.assert_called_once_with(self.user, User.PasswordLinkPurpose.RESET)

    def test_staff_can_invite_an_inactive_user(self) -> None:
        connection = Mock()
        connection.send_messages.return_value = 1
        self.client.force_authenticate(self.admin)

        with patch("users.services._email_connection", return_value=connection):
            response = self.client.post(
                "/api/users/invite/",
                {"name": "Invited", "email": "invited@example.test"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        invited = User.objects.get(email="invited@example.test")
        self.assertFalse(invited.is_active)
        self.assertFalse(invited.has_usable_password())
        self.assertEqual(
            invited.password_link_purpose,
            User.PasswordLinkPurpose.INVITATION,
        )
        self.assertTrue(invited.password_link_token_hash)

    @override_settings(PUBLIC_URL="https://finanzen.example")
    def test_link_uses_the_configured_public_url(self) -> None:
        self.assertEqual(
            password_link_url("special-token"),
            "https://finanzen.example/reset-password/special-token",
        )


class AddUserCommandTests(TestCase):
    def test_adds_admin_to_the_existing_household(self) -> None:
        household = Household.objects.first()
        assert household is not None
        output = StringIO()

        call_command(
            "add_user",
            "NEW@EXAMPLE.TEST",
            name="Neue Person",
            password="Unusual!Password2026",
            admin=True,
            stdout=output,
        )

        user = User.objects.get(email="new@example.test")
        self.assertEqual(user.name, "Neue Person")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_onboarded)
        self.assertEqual(user.current_household, household)
        self.assertTrue(user.households.filter(pk=household.pk).exists())
        self.assertTrue(Category.objects.filter(household=household).exists())
        self.assertIn("Administrator angelegt", output.getvalue())

    def test_rejects_an_existing_email(self) -> None:
        User.objects.create_user(
            email="existing@example.test",
            password="Unusual!Password2026",
        )

        with self.assertRaisesMessage(CommandError, "existiert bereits"):
            call_command(
                "add_user",
                "existing@example.test",
                password="Another!Password2026",
            )
