"""Local SMTP dispatcher. SMTP acceptance is not proof of mailbox delivery."""

import asyncio
import contextlib
import json
import logging
import signal
import smtplib
from email.message import EmailMessage

from app.config import settings
from app.db import engine
from app.notifications import acknowledge, claim_deliveries, prepare, reconcile

log = logging.getLogger("servicepulse.dispatcher")


def send_smtp(payload):
    message = EmailMessage()
    message["From"] = settings.smtp_sender
    message["To"] = payload["email"]
    message["Subject"] = (
        f"ServicePulse {payload['event_type']}: "
        f"{'Падение' if payload['event_type'] == 'DOWN' else 'Восстановление'} "
        f"{' '.join(payload['monitor_name'].splitlines())}"
    )
    message["Message-ID"] = f"<{payload['delivery_id']}@servicepulse.local>"
    message["X-ServicePulse-Incident"] = payload["incident_id"]
    message["X-ServicePulse-Event"] = payload["event_type"]
    message.set_content(
        f"Сервис: {payload['monitor_name']}\n"
        f"Событие: {'Падение' if payload['event_type'] == 'DOWN' else 'Восстановление'}\n"
        f"Инцидент: {payload['incident_id']}\nПодтверждённое падение: {payload['opened_at']}\n"
        f"Восстановление: {payload['recovered_at'] or 'не подтверждено'}\n"
    )
    smtp = smtplib.SMTP(
        settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds
    )
    try:
        smtp.send_message(message)
    finally:
        # DATA's success reply defines acceptance; a failed QUIT cannot undo that acceptance.
        smtp.close()


def classify_error(exc):
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        permanent = all(code >= 500 for code, _ in exc.recipients.values())
        return "smtp_permanent" if permanent else "smtp_temporary", permanent, True
    if isinstance(exc, smtplib.SMTPResponseException):
        permanent = exc.smtp_code >= 500
        return "smtp_permanent" if permanent else "smtp_temporary", permanent, True
    if isinstance(exc, ValueError):
        return "invalid_message", True, True
    return (
        "smtp_timeout" if isinstance(exc, TimeoutError) else "smtp_network",
        False,
        isinstance(exc, ConnectionRefusedError),
    )


async def dispatch_one(claim, sender=None):
    payload = await prepare(claim)
    if payload is None:
        return
    try:
        if sender is None:
            await asyncio.to_thread(send_smtp, payload)
        else:
            await sender(payload)
    except (OSError, smtplib.SMTPException, ValueError) as exc:
        category, permanent, definite = classify_error(exc)
        await acknowledge(claim, category, permanent, definite)
        log.warning(
            json.dumps(
                {"event": "smtp_attempt_failed", "delivery_id": str(claim.id), "category": category}
            )
        )
    else:
        await acknowledge(claim)


async def run():
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)
    try:
        while not stop.is_set():
            try:
                await reconcile()
                claims = await claim_deliveries(5, settings.smtp_timeout_seconds * 20 + 30)
                await asyncio.gather(*(dispatch_one(row) for row in claims))
            except Exception as exc:
                log.error(
                    json.dumps({"event": "dispatcher_tick_failed", "type": type(exc).__name__})
                )
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), timeout=2)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    asyncio.run(run())
