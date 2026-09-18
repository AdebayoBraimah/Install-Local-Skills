from litsearch.providers import Providers
from litsearch.auth import Credentials
from litsearch.state import State, Blocked
from test_state import NOW, account
from test_auth import Keychain
import pytest


class Response:
    status_code = 200
    headers = {}

    def __init__(self, data, status=200):
        self.data = data
        self.status_code = status

    def json(self):
        return self.data


class Transport:
    def __init__(self):
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if url.endswith("/me"):
            return Response(account(1000))
        return Response(
            {
                "organic_results": [
                    {"title": "Paper", "data_cid": "0123", "api_key": "secret"}
                ]
            }
        )


def provider(tmp_path, transport=None):
    k = Keychain()
    k.value = "secret"
    return Providers(
        State(tmp_path, clock=lambda: NOW),
        Credentials(backend=k),
        transport or Transport(),
    )


def test_resume_and_secret_redaction(tmp_path):
    p = provider(tmp_path)
    params = {"engine": "google_scholar", "q": "test", "page": 1, "num": 20}
    a = p.request("searchapi", "r", params)
    assert a == p.request("searchapi", "r", params)
    assert len(p.http.calls) == 2
    assert "secret" not in str(a)
    assert p.http.calls[1][1]["headers"] == {"Authorization": "Bearer secret"}
    p.request("searchapi", "r", params, refresh=True)
    assert len(p.http.calls) == 4


def test_auth_error_does_not_retry_fallback(tmp_path):
    t = Transport()
    t.get = lambda *a, **k: Response({}, 401)
    p = provider(tmp_path, t)
    with pytest.raises(Blocked, match="authentication"):
        p.request("searchapi", "r", {"q": "x"})


def test_resume_keeps_retrieval_time(tmp_path):
    from litsearch.workflow import Workflow

    p = provider(tmp_path)
    w = Workflow(p)
    first = w.search("r", "test")["records"][0]["provenance"]
    p.state.clock = lambda: NOW + 8 * 86400
    assert w.search("r", "test")["records"][0]["provenance"] == first


def test_transient_retries_reserve_every_attempt(tmp_path):
    t = Transport()
    original = t.get
    attempt = [0]

    def get(url, **kwargs):
        if url.endswith("/me"):
            return original(url, **kwargs)
        attempt[0] += 1
        return (
            Response({}, 503) if attempt[0] < 3 else Response({"organic_results": []})
        )

    t.get = get
    p = provider(tmp_path, t)
    p.sleep = lambda _: None
    assert p.request("searchapi", "r", {"q": "x"})["organic_results"] == []
    assert p.state.usage("r")["attempts"][0]["requests"] == 3


def test_rate_limit_retry_after_is_persisted(tmp_path):
    t = Transport()
    original = t.get

    def get(url, **kwargs):
        if url.endswith("/me"):
            return original(url, **kwargs)
        r = Response({}, 429)
        r.headers = {"Retry-After": "600"}
        return r

    t.get = get
    p = provider(tmp_path, t)
    with pytest.raises(Blocked, match="rate_limited"):
        p.request("searchapi", "r", {"q": "x"})
    with pytest.raises(Blocked, match="rate_limited"):
        p.request("searchapi", "r2", {"q": "y"})
    assert p.state.usage("r")["attempts"][0]["requests"] == 1
    assert p.state.usage("r2")["attempts"] == []


def test_timeout_outcome_is_charged(tmp_path):
    import requests

    t = Transport()
    original = t.get

    def get(url, **kwargs):
        if url.endswith("/me"):
            return original(url, **kwargs)
        raise requests.Timeout("secret in error must not escape")

    t.get = get
    p = provider(tmp_path, t)
    p.sleep = lambda _: None
    with pytest.raises(Blocked, match="timeout_uncertain") as e:
        p.request("searchapi", "r", {"q": "x"})
    assert "secret" not in str(e.value)
    assert p.state.usage("r")["attempts"][0]["requests"] == 3


def test_openalex_prepaid_budget_never_added(tmp_path):
    p = provider(tmp_path)
    r = Response({})
    r.headers = {"X-RateLimit-Limit": "50000", "X-RateLimit-Remaining": "40000"}
    p.http.get = lambda *a, **k: r
    budget = p.account("openalex", {"Authorization": "Bearer fixture"}, 1)
    assert budget == {"free_limit": 10000, "free_remaining": 0}
    with pytest.raises(Blocked):
        p.state.reserve("openalex", "r", lambda: budget, 1)


def test_malformed_provider_payload_is_structured_failure(tmp_path):
    t = Transport()
    original = t.get
    t.get = lambda url, **kwargs: (
        original(url, **kwargs) if url.endswith("/me") else Response([])
    )
    p = provider(tmp_path, t)
    with pytest.raises(Blocked, match="invalid_provider_response"):
        p.request("searchapi", "r", {"q": "x"})
