"""Provider transport. Every outbound metered attempt has a durable reservation."""

import datetime as dt
from email.utils import parsedate_to_datetime
import math
import time
import requests
from .state import Blocked, digest


class Providers:
    def __init__(self, state, credentials, http=None, sleep=time.sleep):
        self.state, self.auth = state, credentials
        self.http = http or requests.Session()
        if isinstance(self.http, requests.Session):
            self.http.trust_env = False
        self.sleep = sleep
        self.sources = {}
        self.accounts = {}

    def credential(self, provider):
        key, source = self.auth.get(provider)
        self.sources[provider] = source
        return {"Authorization": "Bearer " + key} if key else {}

    def raw(self, url, headers, params=None):
        try:
            response = self.http.get(
                url,
                params=params or {},
                headers=headers,
                timeout=(10, 40),
                allow_redirects=False,
            )
        except requests.RequestException:
            raise Blocked("transport_unavailable") from None
        if response.status_code in (401, 403):
            raise Blocked("authentication_failed")
        if response.status_code != 200:
            raise Blocked("account_unavailable", {"http_status": response.status_code})
        try:
            return response, response.json()
        except ValueError:
            raise Blocked("invalid_provider_response") from None

    def account(self, provider, headers, units):
        if provider == "searchapi":
            _, data = self.raw("https://www.searchapi.io/api/v1/me", headers)
            self.accounts[provider] = self.auth.clean(data)
            return data
        if units == 0:
            return {}
        # Anonymous /rate-limit requires authentication. Probe a free entity to
        # obtain usage headers, never a billable search to discover the balance.
        url = (
            "https://api.openalex.org/rate-limit"
            if headers
            else "https://api.openalex.org/works/W2741809807"
        )
        r, data = self.raw(url, headers)
        cap = 10000 if headers else 1000
        try:
            # Headers are credits, one credit = $0.0001. Paid balance must not
            # inflate free allowance. Total usage is required for higher plans.
            limit = int(r.headers["X-RateLimit-Limit"])
            remaining = int(r.headers["X-RateLimit-Remaining"])
            used = max(0, limit - remaining)
        except (KeyError, TypeError, ValueError):
            try:
                usage = data["daily_usage"]
                used = math.ceil(float(usage["usd_used"]) * 10000)
            except (KeyError, TypeError, ValueError):
                raise Blocked("openalex_free_budget_unavailable") from None
        result = {"free_limit": cap, "free_remaining": max(0, cap - used)}
        self.accounts[provider] = result
        return result

    def request(self, provider, run, params=None, path="works", refresh=False):
        params = params or {}
        if provider not in ("searchapi", "openalex"):
            raise ValueError("provider")
        if provider == "openalex" and not (
            path == "works" or path.startswith("works/")
        ):
            raise ValueError("path")
        key = digest([provider, path, params])
        with self.state.request_lock(key):
            cached = self.state.get(run, key, refresh)
            if cached is not None:
                return cached
            headers = self.credential(provider)
            units = (
                1
                if provider == "searchapi"
                else (
                    0 if path.startswith("works/") else 10 if "search" in params else 1
                )
            )
            url = (
                "https://www.searchapi.io/api/v1/search"
                if provider == "searchapi"
                else "https://api.openalex.org/" + path
            )
            for retry in range(3):
                attempt = self.state.reserve(
                    provider, run, lambda: self.account(provider, headers, units), units
                )
                try:
                    r = self.http.get(
                        url,
                        params=params,
                        headers=headers,
                        timeout=(10, 40),
                        allow_redirects=False,
                    )
                except requests.RequestException:
                    self.state.finish(attempt, "uncertain")
                    if retry < 2:
                        self.sleep(2**retry)
                        continue
                    raise Blocked("timeout_uncertain") from None
                if r.status_code in (401, 403):
                    self.state.finish(attempt, "authentication_failed")
                    raise Blocked("authentication_failed")
                if r.status_code == 429:
                    seconds = 60
                    try:
                        seconds = max(1, float(r.headers.get("Retry-After", 60)))
                    except ValueError:
                        try:
                            seconds = max(
                                1,
                                parsedate_to_datetime(
                                    r.headers["Retry-After"]
                                ).timestamp()
                                - self.state.clock(),
                            )
                        except (ValueError, KeyError, TypeError):
                            pass
                    self.state.hold(provider, seconds)
                    self.state.finish(attempt, "rate_limited")
                    raise Blocked("rate_limited", {"retry_after": seconds})
                if r.status_code >= 500:
                    self.state.finish(attempt, "server_error")
                    if retry < 2:
                        self.sleep(2**retry)
                        continue
                    raise Blocked("provider_unavailable")
                if r.status_code != 200:
                    self.state.finish(attempt, "http_error")
                    raise Blocked("provider_http_error", {"http_status": r.status_code})
                try:
                    data = self.auth.clean(r.json())
                    if not isinstance(data, dict) or not isinstance(
                        data.get("search_metadata", {}), dict
                    ):
                        raise ValueError()
                except ValueError:
                    self.state.finish(attempt, "invalid_response")
                    raise Blocked("invalid_provider_response") from None
                if data.get("error") or data.get("search_metadata", {}).get(
                    "status"
                ) in ("Error", "Failed"):
                    self.state.finish(attempt, "provider_error")
                    raise Blocked("provider_error")
                data["_litsearch_retrieved_at"] = dt.datetime.fromtimestamp(
                    self.state.clock(), dt.timezone.utc
                ).isoformat()
                self.state.put(run, key, data)
                self.state.finish(attempt, "complete")
                return data

    def content_headers(self, run):
        headers = self.credential("openalex")
        if not headers:
            raise Blocked("openalex_content_key_required")
        attempt = self.state.reserve(
            "openalex", run, lambda: self.account("openalex", headers, 100), 100
        )
        return headers, attempt
