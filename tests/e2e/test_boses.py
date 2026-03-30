"""
Boses e2e tests — run against the staging URL via Playwright.
These verify the core user flows work end-to-end.
"""
import pytest
from playwright.sync_api import Page, expect


def test_homepage_loads(page: Page, base_url: str):
    page.goto(base_url)
    expect(page).not_to_have_title("")


def test_dashboard_loads(page: Page, base_url: str):
    page.goto(f"{base_url}/dashboard")
    page.wait_for_load_state("networkidle")
    expect(page.locator("body")).to_be_visible()


def test_projects_page_loads(page: Page, base_url: str):
    page.goto(f"{base_url}/projects")
    page.wait_for_load_state("networkidle")
    expect(page.locator("body")).to_be_visible()


def test_no_console_errors(page: Page, base_url: str):
    errors = []
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    page.goto(f"{base_url}/dashboard")
    page.wait_for_load_state("networkidle")
    # Allow known third-party errors, fail on app errors
    app_errors = [e for e in errors if "temujintechnologies" in e or "localhost" in e]
    assert len(app_errors) == 0, f"Console errors found: {app_errors}"
