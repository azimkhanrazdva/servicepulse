import asyncio
import time
from dataclasses import dataclass

import httpx

from app.config import settings
from app.security import UnsafeTarget, pinned_target


@dataclass
class Observation:
    success: bool
    status_code: int | None
    response_ms: float
    error: str | None


async def check(monitor, client: httpx.AsyncClient):
    start = time.perf_counter()
    status = None
    error = None
    success = False
    try:
        async with asyncio.timeout(monitor.timeout_seconds):
            url, host, sni = await pinned_target(monitor.url)
            async with client.stream(
                "GET",
                url,
                # Numeric-IP pool keys must not reuse TLS sessions across virtual hosts.
                headers={"Host": host, "Accept-Encoding": "identity", "Connection": "close"},
                extensions={"sni_hostname": sni},
                timeout=monitor.timeout_seconds,
                follow_redirects=False,
            ) as response:
                status = response.status_code
                if response.headers.get("content-encoding", "identity") != "identity":
                    raise ValueError("encoded_response")
                body = bytearray()
                async for chunk in response.aiter_raw():
                    body.extend(chunk)
                    if len(body) > settings.max_body_bytes:
                        raise ValueError("body_too_large")
                success = status == monitor.expected_status and (
                    not monitor.expected_body
                    or monitor.expected_body in body.decode("utf-8", "replace")
                )
                if not success:
                    error = (
                        "unexpected_status"
                        if status != monitor.expected_status
                        else "body_mismatch"
                    )
    except UnsafeTarget:
        error = "blocked_destination"
    except (TimeoutError, httpx.TimeoutException):
        error = "timeout"
    except (httpx.HTTPError, OSError):
        error = "network_error"
    except ValueError as exc:
        error = (
            str(exc) if str(exc) in {"encoded_response", "body_too_large"} else "invalid_response"
        )
    return Observation(success, status, round((time.perf_counter() - start) * 1000, 2), error)


def transition(state: str, failures: int, success: bool, threshold: int):
    if state == "PAUSED":
        return state, failures
    if success:
        return "UP", 0
    failures += 1
    return ("DOWN" if failures >= threshold else state), failures
