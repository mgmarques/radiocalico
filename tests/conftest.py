"""Fixtures for end-to-end tests against the running Docker prod stack."""

import os

import pytest


@pytest.fixture
def base_url():
    """Base URL of the running application."""
    return os.environ.get('E2E_BASE_URL', 'http://127.0.0.1:5050')
