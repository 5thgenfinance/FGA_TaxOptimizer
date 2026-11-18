from app import auth_gate


def test_correct_password_is_accepted():
    assert auth_gate.password_ok("correct horse", ["correct horse"])


def test_wrong_and_empty_passwords_are_rejected():
    assert not auth_gate.password_ok("wrong", ["correct horse"])
    assert not auth_gate.password_ok("", ["correct horse"])


def test_any_listed_password_is_accepted_during_a_rotation():
    accepted = ["new-one", "old-one"]
    assert auth_gate.password_ok("old-one", accepted)
    assert auth_gate.password_ok("new-one", accepted)


def test_non_ascii_passwords_work():
    assert auth_gate.password_ok("p\u00e4ss\u00df", ["p\u00e4ss\u00df"])


def test_accepted_passwords_reads_both_secret_names():
    secrets = {"app_password": "one", "app_passwords": ["two", "three"]}
    assert auth_gate.accepted_passwords(secrets) == ["one", "two", "three"]


def test_blank_passwords_are_ignored_so_the_gate_cannot_open_on_an_empty_entry():
    assert auth_gate.accepted_passwords({"app_password": ""}) == []
    assert auth_gate.accepted_passwords({}) == []


def test_no_secrets_means_the_gate_is_off():
    class NoSecrets:
        def __contains__(self, key):
            raise FileNotFoundError("no secrets file")

    assert auth_gate.accepted_passwords(NoSecrets()) == []
