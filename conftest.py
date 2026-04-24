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
    with patch('services.email.resend.Emails.send') as mock:
        yield mock