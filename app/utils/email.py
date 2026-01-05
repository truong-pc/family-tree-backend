import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings


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
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_USER
        msg["To"] = to_email
        
        part1 = MIMEText(text_body, "plain")
        part2 = MIMEText(html_body, "html")
        msg.attach(part1)
        msg.attach(part2)
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
        
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
