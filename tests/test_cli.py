"""The two admin command-line scripts: account creation and couple creation.

Both must work on a completely fresh database (they run db/auth/couples init
themselves) because in production they run inside the Docker container.
"""

from pathlib import Path

import pytest

from server import auth, couples, create_couple, create_user, db


@pytest.fixture(autouse=True)
def temp_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "library.db")
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)


def test_create_user_and_reset(capsys: pytest.CaptureFixture) -> None:
    assert create_user.main(
        ["viktor", "--role", "admin", "--password", "first-password-1"]
    ) == 0
    assert auth.authenticate("viktor", "first-password-1").is_admin

    assert create_user.main(
        ["viktor", "--reset", "--password", "second-password-2"]
    ) == 0
    assert auth.authenticate("viktor", "second-password-2").is_admin
    capsys.readouterr()


def test_create_user_refuses_duplicates_and_weak_passwords(
    capsys: pytest.CaptureFixture,
) -> None:
    assert create_user.main(["sarah", "--password", "long-enough-pw"]) == 0
    assert create_user.main(["sarah", "--password", "another-long-pw"]) == 1
    assert "already an account" in capsys.readouterr().err
    assert create_user.main(["kim", "--password", "short"]) == 1


def test_create_couple_defaults_to_the_admin(capsys: pytest.CaptureFixture) -> None:
    create_user.main(["viktor", "--role", "admin", "--password", "first-password-1"])
    capsys.readouterr()

    assert create_couple.main(["Sofie & Jan", "2027-05-25"]) == 0
    out = capsys.readouterr().out
    assert out.count("/g/") == 2  # both magic links printed

    listed = couples.list_couples()
    admin_id = auth.find_by_username("viktor")["id"]
    assert [(couple["names"], couple["dj_id"]) for couple in listed] == [
        ("Sofie & Jan", admin_id)
    ]


def test_create_couple_for_a_dj_with_public_base_url(
    capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    create_user.main(["sarah", "--password", "long-enough-pw"])
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://rekord.example.com/")
    capsys.readouterr()

    assert create_couple.main(["Kim & Alex", "2027-06-01", "--dj", "sarah"]) == 0
    out = capsys.readouterr().out
    assert "https://rekord.example.com/g/" in out

    couple = couples.list_couples()[0]
    assert couple["dj_id"] == auth.find_by_username("sarah")["id"]


def test_create_couple_errors_are_clean(capsys: pytest.CaptureFixture) -> None:
    # No admin yet, and unknown DJs or bad dates must not stack-trace.
    assert create_couple.main(["A & B", "2027-01-01"]) == 1
    assert "No admin account" in capsys.readouterr().err
    create_user.main(["viktor", "--role", "admin", "--password", "first-password-1"])
    assert create_couple.main(["A & B", "2027-01-01", "--dj", "ghost"]) == 1
    assert create_couple.main(["A & B", "someday"]) == 1
