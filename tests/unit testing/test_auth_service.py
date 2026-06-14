from unittest.mock import MagicMock, patch

from app.services.auth_service import AuthService


# UT-01
def test_authenticate_returns_user_when_credentials_valid():
    mock_user = MagicMock()
    mock_user.password = "hashed-password"

    with patch("app.services.auth_service.User") as MockUser, \
            patch("app.services.auth_service.check_password_hash", return_value=True):
        MockUser.query.filter_by.return_value.first.return_value = mock_user

        result = AuthService.authenticate("user@example.com", "password")

    assert result is mock_user

# UT-02
def test_authenticate_returns_none_when_user_not_found():
    with patch("app.services.auth_service.User") as MockUser:
        MockUser.query.filter_by.return_value.first.return_value = None

        result = AuthService.authenticate("notfound@example.com", "password")

    assert result is None

# UT-03
def test_authenticate_returns_none_when_password_incorrect():
    mock_user = MagicMock()
    mock_user.password = "hashed-password"

    with patch("app.services.auth_service.User") as MockUser, \
            patch("app.services.auth_service.check_password_hash", return_value=False):
        MockUser.query.filter_by.return_value.first.return_value = mock_user

        result = AuthService.authenticate("user@example.com", "wrong-password")

    assert result is None

# UT-04
def test_update_password_success():
    user = MagicMock()
    user.password = "old-hash"

    with patch("app.services.auth_service.check_password_hash", return_value=True), \
            patch("app.services.auth_service.generate_password_hash", return_value="new-hash"), \
            patch("app.services.auth_service.db") as mock_db:
        ok, message = AuthService.update_password(user, "current-password", "PasswordBaru123")

    assert ok is True
    assert message == "Password berhasil diperbarui."
    assert user.password == "new-hash"
    mock_db.session.commit.assert_called_once()

# UT-05
def test_update_password_fails_when_current_password_wrong():
    user = MagicMock()
    user.password = "old-hash"

    with patch("app.services.auth_service.check_password_hash", return_value=False), \
            patch("app.services.auth_service.db") as mock_db:
        ok, message = AuthService.update_password(user, "wrong-current", "PasswordBaru123")

    assert ok is False
    assert message == "Password saat ini tidak sesuai."
    assert user.password == "old-hash"
    mock_db.session.commit.assert_not_called()

# UT-06
def test_update_password_fails_when_new_password_too_short():
    user = MagicMock()
    user.password = "old-hash"

    with patch("app.services.auth_service.check_password_hash", return_value=True), \
            patch("app.services.auth_service.db") as mock_db:
        ok, message = AuthService.update_password(user, "current-password", "12345")

    assert ok is False
    assert message == "Password baru minimal 6 karakter."
    assert user.password == "old-hash"
    mock_db.session.commit.assert_not_called()
