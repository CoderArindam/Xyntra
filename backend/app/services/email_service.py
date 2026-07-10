import smtplib
import logging
from email.message import EmailMessage

from app.config.settings import settings


logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, body_text: str) -> bool:

    if not settings.SMTP_EMAIL or not settings.SMTP_PASSWORD:
        logger.warning(
            "SMTP credentials missing. Skipping email."
        )
        return False


    msg = EmailMessage()

    msg["From"] = settings.SMTP_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.set_content(body_text)


    try:

        with smtplib.SMTP(
            "smtp.gmail.com",
            587
        ) as server:

            server.starttls()

            server.login(
                settings.SMTP_EMAIL,
                settings.SMTP_PASSWORD
            )

            server.send_message(msg)


        logger.info(f"Email sent to {to_email}")

        return True


    except Exception as e:

        logger.error(
            f"Email failed: {e}"
        )

        return False