import pytest
from litsearch.auth import Credentials
from litsearch.state import Blocked


class Keychain:
    value = None

    def get_password(self, *a):
        return self.value

    def set_password(self, *a):
        self.value = a[-1]


def test_literal_file_and_rotation(tmp_path):
    p = tmp_path / "key.env"
    p.write_text('SEARCH_API_KEY="$(touch /tmp/should-not-run)"\n')
    p.chmod(0o600)
    k = Keychain()
    c = Credentials(p, k)
    assert c.get("searchapi") == ("$(touch /tmp/should-not-run)", "file")
    c.import_file()
    assert c.get("searchapi")[1] == "keychain"
    p.write_text("SEARCH_API_KEY=rotated\n")
    c.import_file()
    assert c.get("searchapi")[0] == "rotated"
    assert "rotated" not in str(c.status())


def test_unsafe_permissions_refused(tmp_path):
    p = tmp_path / "key.env"
    p.write_text("SEARCH_API_KEY=secret")
    p.chmod(0o644)
    with pytest.raises(Blocked):
        Credentials(p, Keychain()).get("searchapi")


def test_keychain_failure_fallback_and_duplicate_assignments(tmp_path):
    class Missing(Keychain):
        def get_password(self, *args):
            raise RuntimeError("do not print")

    p = tmp_path / "key.env"
    p.write_text("SEARCH_API_KEY=literal")
    p.chmod(0o600)
    assert Credentials(p, Missing()).get("searchapi") == ("literal", "file")
    p.write_text("SEARCH_API_KEY=a\nSEARCH_API_KEY=b")
    with pytest.raises(Blocked, match="invalid_credential_file"):
        Credentials(p, Missing()).get("searchapi")


def test_symlink_credential_file_refused(tmp_path):
    p = tmp_path / "actual"
    p.write_text("SEARCH_API_KEY=literal")
    p.chmod(0o600)
    link = tmp_path / "link"
    link.symlink_to(p)
    with pytest.raises(Blocked):
        Credentials(link, Keychain()).get("searchapi")
