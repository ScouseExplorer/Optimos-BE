import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    pass


class EmailService:
    @staticmethod
    def ensure_configured() -> None:
        if not settings.RESEND_API_KEY or not settings.EMAIL_FROM:
            raise EmailDeliveryError("Email delivery is not configured")

    async def send_email(self, recipient: str, subject: str, html: str, text: str) -> None:
        self.ensure_configured()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                    json={
                        "from": settings.EMAIL_FROM,
                        "to": [recipient],
                        "subject": subject,
                        "html": html,
                        "text": text,
                    },
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Resend email delivery failed: %s", exc.__class__.__name__)
            raise EmailDeliveryError("Email delivery failed") from exc


email_service = EmailService()
