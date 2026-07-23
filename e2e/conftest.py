import os

import pytest


@pytest.fixture(scope="session")
def app_url():
    return os.getenv("E2E_BASE_URL", "http://localhost").rstrip("/")


@pytest.fixture(autouse=True)
def fail_on_browser_errors(page):
    errors = []

    page.on("pageerror", lambda error: errors.append(f"page error: {error}"))
    page.on(
        "console",
        lambda message: errors.append(f"console error: {message.text}")
        if message.type == "error"
        else None,
    )
    page.set_default_timeout(10_000)

    yield

    assert not errors, "Browser errors:\n" + "\n".join(errors)
