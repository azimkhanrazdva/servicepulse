"""Fault helper for the isolated stack: exit AFTER actual SMTP acceptance, BEFORE DB ack."""

import asyncio
import os

from app.dispatcher import send_smtp
from app.notifications import claim_deliveries, prepare


async def main():
    claims = await claim_deliveries(1, lease_seconds=2)
    assert len(claims) == 1
    payload = await prepare(claims[0])
    assert payload is not None
    await asyncio.to_thread(send_smtp, payload)
    os._exit(73)  # Intentional isolated fault, persisted send_started_at but no sent_at.


if __name__ == "__main__":
    asyncio.run(main())
