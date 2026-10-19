from types import SimpleNamespace

import httpx
import pytest

from app.checker import check, transition
from app.config import settings
from app.schemas import MonitorCreate
from app.security import UnsafeTarget, pinned_target, validate_url


@pytest.mark.parametrize(
    "initial,failures,success,expected",
    [
        ("UNKNOWN", 0, True, ("UP", 0)),
        ("UNKNOWN", 0, False, ("UNKNOWN", 1)),
        ("UP", 0, False, ("UP", 1)),
        ("UP", 1, False, ("DOWN", 2)),
        ("DOWN", 3, True, ("UP", 0)),
        ("PAUSED", 0, False, ("PAUSED", 0)),
    ],
)
def test_transition(initial, failures, success, expected):
    assert transition(initial, failures, success, 2) == expected


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com",
        "http://u:p@x",
        "http://x/#fragment",
        "http://[fe80::1%eth0]/",
        "http://x:99999",
    ],
)
def test_url_rejects(url):
    with pytest.raises(UnsafeTarget):
        validate_url(url)


@pytest.mark.parametrize(
    "field,value",
    [
        ("interval_seconds", 29),
        ("interval_seconds", 3601),
        ("timeout_seconds", 0),
        ("expected_status", 600),
        ("failure_threshold", 0),
    ],
)
def test_settings_bounds(field, value):
    with pytest.raises(ValueError):
        MonitorCreate(name="test", url="https://example.com", **{field: value})


async def test_dns_policy_and_pinning(monkeypatch):
    async def resolve(host, port, **kwargs):
        return [(2, 1, 6, "", ("127.0.0.1", port))]

    import asyncio

    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", resolve)
    monkeypatch.setattr(settings, "simulator_origin", "")
    with pytest.raises(UnsafeTarget):
        await pinned_target("http://example.com")
    monkeypatch.setattr(settings, "simulator_origin", "http://simulator:8090")
    url, host, sni = await pinned_target("http://simulator:8090/target/demo")
    assert str(url) == "http://127.0.0.1:8090/target/demo"
    assert host == "simulator:8090" and sni == "simulator"
    with pytest.raises(UnsafeTarget):
        await pinned_target("http://simulator:8000/")


class Body(httpx.AsyncByteStream):
    def __init__(self, data):
        self.data = data

    async def __aiter__(self):
        yield self.data


@pytest.mark.parametrize(
    "status,body,expected,error",
    [
        (200, b"ready", "ready", None),
        (500, b"ready", None, "unexpected_status"),
        (200, b"wrong", "ready", "body_mismatch"),
    ],
)
async def test_http_and_body(monkeypatch, status, body, expected, error):
    async def pinned(value):
        return httpx.URL("https://93.184.215.14/"), "example.com", "example.com"

    monkeypatch.setattr("app.checker.pinned_target", pinned)

    def response(request):
        assert request.headers["Host"] == "example.com"
        assert request.extensions["sni_hostname"] == "example.com"
        return httpx.Response(status, stream=Body(body))

    async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
        result = await check(
            SimpleNamespace(
                url="https://example.com",
                timeout_seconds=1,
                expected_status=200,
                expected_body=expected,
            ),
            client,
        )
    assert result.error == error
    assert result.success == (error is None)


async def test_total_timeout_includes_dns(monkeypatch):
    import asyncio

    async def slow(value):
        await asyncio.sleep(1)

    monkeypatch.setattr("app.checker.pinned_target", slow)
    async with httpx.AsyncClient() as client:
        result = await check(
            SimpleNamespace(url="https://example.com", timeout_seconds=0.01), client
        )
    assert result.error == "timeout"


@pytest.mark.parametrize(
    "status,headers,body,error",
    [
        (302, {"location": "http://127.0.0.1/"}, b"", "unexpected_status"),
        (200, {"content-encoding": "gzip"}, b"compressed", "encoded_response"),
        (200, {}, b"x" * 2048, "body_too_large"),
    ],
)
async def test_bounded_body_and_no_redirect(monkeypatch, status, headers, body, error):
    async def pinned(value):
        return httpx.URL("http://93.184.215.14/"), "example.com", "example.com"

    monkeypatch.setattr("app.checker.pinned_target", pinned)
    monkeypatch.setattr(settings, "max_body_bytes", 1024)
    calls = []

    def response(request):
        calls.append(request)
        assert request.headers["Connection"] == "close"
        return httpx.Response(status, headers=headers, stream=Body(body))

    async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
        result = await check(
            SimpleNamespace(
                url="http://example.com", timeout_seconds=1, expected_status=200, expected_body=None
            ),
            client,
        )
    assert result.error == error and not result.success
    assert len(calls) == 1


async def test_mixed_public_private_dns_is_blocked(monkeypatch):
    import asyncio

    async def resolve(host, port, **kwargs):
        return [(2, 1, 6, "", (ip, port)) for ip in ["93.184.215.14", "10.1.2.3"]]

    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", resolve)
    monkeypatch.setattr(settings, "simulator_origin", "")
    with pytest.raises(UnsafeTarget):
        await pinned_target("https://example.com")


def test_custom_threshold():
    assert transition("UP", 0, False, 1) == ("DOWN", 1)
    assert transition("UP", 2, False, 4) == ("UP", 3)
