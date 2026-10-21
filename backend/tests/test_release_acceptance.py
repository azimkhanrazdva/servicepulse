"""Release-boundary checks that were previously documented but not directly exercised."""

import httpx

from app.db import session_dependency
from app.main import app


async def test_management_exception_never_exposes_internal_details():
    class BrokenDatabase:
        async def execute(self, *args):
            raise RuntimeError("PRIVATE-DATABASE-CREDENTIAL-SENTINEL")

    async def broken_session():
        yield BrokenDatabase()

    app.dependency_overrides[session_dependency] = broken_session
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://localhost",
        ) as api:
            response = await api.get("/api/ready")
        assert response.status_code == 500
        assert response.text == "Internal Server Error"
        assert "SENTINEL" not in response.text and "Traceback" not in response.text
    finally:
        del app.dependency_overrides[session_dependency]
