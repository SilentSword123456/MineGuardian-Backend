from unittest.mock import patch
import pytest
from api import app, limiter

@pytest.fixture(autouse=True)
def disable_rate_limiting():
    app.config['RATELIMIT_ENABLED'] = False
    # or, if that config key doesn't work for your version:
    limiter.enabled = False
    yield
    limiter.enabled = True

@pytest.fixture(autouse=True)
def mock_email(autouse=True):
    # the email helper lives in services/emailService.py (module name: services.emailService)
    # patch the resend.Emails.send used by that module
    with patch('services.emailService.resend.Emails.send') as mock:
        yield mock