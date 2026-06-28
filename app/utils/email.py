import logging
import anyio
import resend
from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_otp_email(to_email: str, otp: str) -> bool:
    """
    Send OTP code to user's email for password reset.
    Returns True if email sent successfully, False otherwise.
    """
    subject = f"[{settings.APP_NAME}] Password Reset OTP"
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 30px; border-radius: 10px;">
            <h2 style="color: #333;">Password Reset Request</h2>
            <p>You have requested to reset your password. Use the OTP code below to proceed:</p>
            <div style="background-color: #007bff; color: white; font-size: 32px; font-weight: bold; text-align: center; padding: 20px; border-radius: 5px; letter-spacing: 5px; margin: 20px 0;">
                {otp}
            </div>
            <p style="color: #666;">This code will expire in <strong>10 minutes</strong>.</p>
            <p style="color: #666;">If you did not request this, please ignore this email.</p>
            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            <p style="color: #999; font-size: 12px;">This is an automated message from {settings.APP_NAME}. Please do not reply.</p>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
Password Reset Request

You have requested to reset your password. Use the OTP code below to proceed:

OTP: {otp}

This code will expire in 10 minutes.

If you did not request this, please ignore this email.

---
This is an automated message from {settings.APP_NAME}. Please do not reply.
    """
    
    if not settings.RESEND_API_KEY:
        logger.error("RESEND_API_KEY is not configured; cannot send email")
        return False

    params: resend.Emails.SendParams = {
        "from": settings.EMAIL_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }

    try:
        resend.api_key = settings.RESEND_API_KEY
        # resend SDK is synchronous; run it off the event loop.
        await anyio.to_thread.run_sync(lambda: resend.Emails.send(params))
        return True
    except Exception:
        logger.exception("Failed to send email")
        return False
