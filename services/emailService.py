import os
import resend

resend.api_key = os.environ.get("RESEND_API_KEY", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")


# noinspection PyTypeChecker
def send_verification_email(to_email: str, token: str, first_name: str=""):
    if os.environ.get("FLASK_ENV") == "development":
        print(f"[DEV] Verification token for {to_email}: {token}")
        return True


    resend.Emails.send({
        "from": "noreply@silentlab.work",
        "to": [to_email],
        "subject": "Verify your MineGuardian email",
        "template": {
            "id": "email-verification-copy",
            "variables": {
                "company_name": "MineGuardian",
                "company_address": "silentlab.work",
                "first_name": first_name,
                "verification_url": f"{FRONTEND_URL}/verifyEmail?token={token}",
            }
        }
    })
    return True


def send_password_reset_email(to_email: str, token: str):
    if os.environ.get("FLASK_ENV") == "development":
        print(f"[DEV] Password reset token for {to_email}: {token}")
        return True

    resend.Emails.send({
        "from": "noreply@silentlab.work",
        "to": to_email,
        "subject": "Reset your MineGuardian password",
        "html": f"<p>Click <a href='{FRONTEND_URL}/reset-password?token={token}'>here</a> to reset your password. Expires in 1 hour.</p>"
    })
    return True