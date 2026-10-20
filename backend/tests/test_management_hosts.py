import httpx
import pytest

from app.main import app


@pytest.mark.parametrize(
    "host,expected",
    [
        ("localhost:8000", 200),
        ("127.0.0.1:8000", 200),
        ("backend:8000", 200),
        ("servicepulse-audit.invalid", 400),
        ("localhost.attacker.example", 400),
    ],
)
async def test_management_rejects_untrusted_host(host, expected):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://localhost"
    ) as api:
        assert (await api.get("/api/health", headers={"Host": host})).status_code == expected
