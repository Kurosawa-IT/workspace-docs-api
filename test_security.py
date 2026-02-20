from app.core.security import hash_password, verify_password


def test_hash_and_verify_ok():
    h = hash_password("correct-horse-battery-staple")
    assert h != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", h) is True


def test_verify_wrong_password_fails():
    h = hash_password("password1")
    assert verify_password("password2", h) is False
