"""
End-to-end tests for negotiation and tournament workflows.

These tests verify the complete user workflows for:
- Starting and running negotiations
- Opening stored negotiations
- Starting and running tournaments
- Opening stored tournaments

Tests both UI functionality and backend data integrity.
"""

import asyncio
import json
import random
import subprocess
import time
from pathlib import Path

import pytest
from playwright.async_api import Browser, Page, async_playwright, expect


# Use a random port in the 5000-6000 range to avoid conflicts
TEST_PORT = random.randint(5000, 6000)
TEST_URL = f"http://127.0.0.1:{TEST_PORT}"


@pytest.fixture(scope="module")
def test_server():
    """Start the app server on a test port for the duration of the module."""
    # Start the server process
    process = subprocess.Popen(
        ["negmas-app", "run", "--port", str(TEST_PORT), "--host", "127.0.0.1"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start (up to 10 seconds)
    max_wait = 10
    for _ in range(max_wait * 10):
        try:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(("127.0.0.1", TEST_PORT))
            sock.close()
            if result == 0:
                break
        except Exception:
            pass
        time.sleep(0.1)
    else:
        process.kill()
        pytest.fail(f"Server failed to start on port {TEST_PORT} within {max_wait}s")

    yield TEST_URL

    # Cleanup: kill the server process
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


@pytest.fixture(scope="module")
async def browser():
    """Start a browser instance for the test module."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser: Browser):
    """Create a new page for each test."""
    page = await browser.new_page()

    # Track console errors
    console_errors = []
    page.on(
        "console",
        lambda msg: console_errors.append(msg) if msg.type == "error" else None,
    )
    page.on("pageerror", lambda error: console_errors.append(str(error)))

    page.console_errors = console_errors  # Attach to page for test access

    yield page
    await page.close()


async def wait_for_no_loading_spinners(page: Page, timeout: int = 30000):
    """Wait for all loading spinners to disappear."""
    await page.wait_for_selector(".loading-spinner", state="hidden", timeout=timeout)


async def check_for_console_errors(page: Page):
    """Check if any console errors occurred and return them."""
    if hasattr(page, "console_errors") and page.console_errors:
        error_msgs = []
        for error in page.console_errors:
            if hasattr(error, "text"):
                error_msgs.append(error.text)
            else:
                error_msgs.append(str(error))
        return error_msgs
    return []


@pytest.mark.asyncio
async def test_start_new_negotiation(page: Page, test_server: str):
    """
    Test starting a new negotiation from the UI.

    Steps:
    1. Navigate to the app
    2. Select a scenario
    3. Select negotiators for each party
    4. Click "Start Negotiation"
    5. Verify negotiation is created and displayed
    6. Verify backend state is correct
    """
    # Navigate to the app
    await page.goto(test_server, wait_until="networkidle")
    await page.wait_for_timeout(2000)  # Wait for Alpine.js initialization

    # Click on Scenarios tab to ensure we're on the right page
    await page.click("text=Scenarios", timeout=5000)
    await page.wait_for_timeout(500)

    # Wait for scenarios to load
    await page.wait_for_selector("[data-scenario-id]", timeout=10000)

    # Click on the first available scenario
    first_scenario = page.locator("[data-scenario-id]").first
    await first_scenario.click()
    await page.wait_for_timeout(1000)

    # Wait for negotiator selectors to appear
    await page.wait_for_selector(".negotiator-selector", timeout=5000)

    # Select negotiators for each party
    negotiator_selects = page.locator(".negotiator-selector select")
    count = await negotiator_selects.count()

    for i in range(count):
        select = negotiator_selects.nth(i)
        # Select a non-empty option (skip the first "Select negotiator" option)
        await select.select_option(index=1)
        await page.wait_for_timeout(200)

    # Click "Start Negotiation" button
    start_button = page.locator("button:has-text('Start Negotiation')")
    await start_button.click()

    # Wait for negotiation to start (should switch to Negotiations tab)
    await page.wait_for_timeout(2000)

    # Verify we're now viewing a negotiation
    # Look for negotiation-specific elements like the control panel
    await page.wait_for_selector(".negotiation-controls", timeout=10000)

    # Verify control buttons are present
    await expect(page.locator("button:has-text('Step')")).to_be_visible()
    await expect(page.locator("button:has-text('Run')")).to_be_visible()

    # Check for console errors
    errors = await check_for_console_errors(page)
    assert not errors, f"Console errors occurred: {errors}"

    # Verify backend state by checking the API
    response = await page.evaluate("""
        async () => {
            const res = await fetch('/api/negotiations');
            return await res.json();
        }
    """)

    assert len(response) > 0, "No negotiations found in backend"
    latest_negotiation = response[0]
    assert latest_negotiation["status"] in ["running", "waiting"], (
        "Negotiation not in expected state"
    )


@pytest.mark.asyncio
async def test_run_negotiation_to_completion(page: Page, test_server: str):
    """
    Test running a negotiation to completion.

    Steps:
    1. Start a new negotiation
    2. Click "Run" button
    3. Wait for negotiation to complete
    4. Verify completion status
    5. Verify results are displayed
    """
    # Navigate and start a negotiation (reuse logic from previous test)
    await page.goto(test_server, wait_until="networkidle")
    await page.wait_for_timeout(2000)

    await page.click("text=Scenarios", timeout=5000)
    await page.wait_for_timeout(500)

    await page.wait_for_selector("[data-scenario-id]", timeout=10000)
    first_scenario = page.locator("[data-scenario-id]").first
    await first_scenario.click()
    await page.wait_for_timeout(1000)

    await page.wait_for_selector(".negotiator-selector", timeout=5000)
    negotiator_selects = page.locator(".negotiator-selector select")
    count = await negotiator_selects.count()

    for i in range(count):
        select = negotiator_selects.nth(i)
        await select.select_option(index=1)
        await page.wait_for_timeout(200)

    start_button = page.locator("button:has-text('Start Negotiation')")
    await start_button.click()
    await page.wait_for_timeout(2000)

    # Now run the negotiation
    await page.wait_for_selector(".negotiation-controls", timeout=10000)
    run_button = page.locator("button:has-text('Run')")
    await run_button.click()

    # Wait for negotiation to complete (up to 30 seconds)
    # Look for completion indicators: status badge, final outcome display
    await page.wait_for_selector(
        "[data-status='completed'], [data-status='failed'], [data-status='agreement'], [data-status='no_agreement']",
        timeout=30000,
    )

    # Verify results are displayed
    # Check for outcome information
    await page.wait_for_selector(
        ".negotiation-outcome, .outcome-display, .agreement-details", timeout=5000
    )

    # Check for console errors
    errors = await check_for_console_errors(page)
    assert not errors, f"Console errors occurred during negotiation run: {errors}"

    # Verify backend shows completion
    response = await page.evaluate("""
        async () => {
            const res = await fetch('/api/negotiations');
            return await res.json();
        }
    """)

    assert len(response) > 0, "No negotiations found"
    latest = response[0]
    assert latest["status"] in ["completed", "failed", "agreement", "no_agreement"], (
        f"Unexpected status: {latest['status']}"
    )


@pytest.mark.asyncio
async def test_open_stored_negotiation(page: Page, test_server: str):
    """
    Test opening a previously stored negotiation.

    Steps:
    1. Ensure at least one negotiation exists
    2. Navigate to Negotiations tab
    3. Click on a stored negotiation
    4. Verify negotiation data loads correctly
    5. Verify visualizations are displayed
    """
    # First, create a negotiation to ensure we have one to open
    await page.goto(test_server, wait_until="networkidle")
    await page.wait_for_timeout(2000)

    # Quick negotiation creation
    await page.click("text=Scenarios", timeout=5000)
    await page.wait_for_timeout(500)
    await page.wait_for_selector("[data-scenario-id]", timeout=10000)
    first_scenario = page.locator("[data-scenario-id]").first
    await first_scenario.click()
    await page.wait_for_timeout(1000)

    await page.wait_for_selector(".negotiator-selector", timeout=5000)
    negotiator_selects = page.locator(".negotiator-selector select")
    count = await negotiator_selects.count()
    for i in range(count):
        select = negotiator_selects.nth(i)
        await select.select_option(index=1)
        await page.wait_for_timeout(200)

    start_button = page.locator("button:has-text('Start Negotiation')")
    await start_button.click()
    await page.wait_for_timeout(2000)

    # Run it to completion
    await page.wait_for_selector(".negotiation-controls", timeout=10000)
    run_button = page.locator("button:has-text('Run')")
    await run_button.click()
    await page.wait_for_timeout(5000)

    # Now go to Negotiations tab to see the list
    await page.click("text=Negotiations", timeout=5000)
    await page.wait_for_timeout(1000)

    # Wait for negotiation list to load
    await page.wait_for_selector(
        "[data-negotiation-id], .negotiation-item", timeout=10000
    )

    # Get the first negotiation ID
    negotiation_item = page.locator("[data-negotiation-id], .negotiation-item").first
    await negotiation_item.click()
    await page.wait_for_timeout(2000)

    # Verify we're viewing the negotiation details
    await page.wait_for_selector(
        ".negotiation-controls, .negotiation-details", timeout=10000
    )

    # Check that visualizations loaded
    # Look for Plotly charts or similar visualization elements
    await page.wait_for_selector(".plotly, canvas, svg.main-svg", timeout=10000)

    # Check for console errors
    errors = await check_for_console_errors(page)
    assert not errors, f"Console errors when opening stored negotiation: {errors}"


@pytest.mark.asyncio
async def test_start_new_tournament(page: Page, test_server: str):
    """
    Test starting a new tournament from the UI.

    Steps:
    1. Navigate to Tournaments tab
    2. Configure tournament settings
    3. Select scenarios
    4. Select negotiator types
    5. Start tournament
    6. Verify tournament is created
    """
    await page.goto(test_server, wait_until="networkidle")
    await page.wait_for_timeout(2000)

    # Go to Tournaments tab
    await page.click("text=Tournaments", timeout=5000)
    await page.wait_for_timeout(1000)

    # Look for "New Tournament" or "Create Tournament" button
    new_tournament_button = page.locator(
        "button:has-text('New Tournament'), button:has-text('Create Tournament')"
    ).first
    await new_tournament_button.click()
    await page.wait_for_timeout(1000)

    # Wait for tournament configuration form
    await page.wait_for_selector(".tournament-config, #tournament-form", timeout=10000)

    # Select at least 2 scenarios (required for tournament)
    scenario_checkboxes = page.locator("input[type='checkbox'][data-scenario-id]")
    count = await scenario_checkboxes.count()
    if count >= 2:
        for i in range(min(2, count)):
            await scenario_checkboxes.nth(i).check()
            await page.wait_for_timeout(200)

    # Select at least 2 negotiator types
    negotiator_checkboxes = page.locator("input[type='checkbox'][data-negotiator-type]")
    count = await negotiator_checkboxes.count()
    if count >= 2:
        for i in range(min(2, count)):
            await negotiator_checkboxes.nth(i).check()
            await page.wait_for_timeout(200)

    # Click "Start Tournament" button
    start_button = page.locator(
        "button:has-text('Start Tournament'), button:has-text('Create Tournament')"
    ).last
    await start_button.click()
    await page.wait_for_timeout(3000)

    # Verify tournament was created
    # Should see tournament view with controls
    await page.wait_for_selector(
        ".tournament-controls, .tournament-view", timeout=10000
    )

    # Check for console errors
    errors = await check_for_console_errors(page)
    assert not errors, f"Console errors when starting tournament: {errors}"

    # Verify backend
    response = await page.evaluate("""
        async () => {
            const res = await fetch('/api/tournaments');
            return await res.json();
        }
    """)

    assert len(response) > 0, "No tournaments found in backend"


@pytest.mark.asyncio
async def test_run_tournament_to_completion(page: Page, test_server: str):
    """
    Test running a tournament to completion.

    Steps:
    1. Create a new tournament
    2. Click "Run" button
    3. Wait for all negotiations to complete
    4. Verify results and leaderboard
    """
    await page.goto(test_server, wait_until="networkidle")
    await page.wait_for_timeout(2000)

    # Create a tournament (reuse logic)
    await page.click("text=Tournaments", timeout=5000)
    await page.wait_for_timeout(1000)

    new_tournament_button = page.locator(
        "button:has-text('New Tournament'), button:has-text('Create Tournament')"
    ).first
    await new_tournament_button.click()
    await page.wait_for_timeout(1000)

    await page.wait_for_selector(".tournament-config, #tournament-form", timeout=10000)

    # Select scenarios and negotiators
    scenario_checkboxes = page.locator("input[type='checkbox'][data-scenario-id]")
    count = await scenario_checkboxes.count()
    if count >= 2:
        for i in range(min(2, count)):
            await scenario_checkboxes.nth(i).check()
            await page.wait_for_timeout(200)

    negotiator_checkboxes = page.locator("input[type='checkbox'][data-negotiator-type]")
    count = await negotiator_checkboxes.count()
    if count >= 2:
        for i in range(min(2, count)):
            await negotiator_checkboxes.nth(i).check()
            await page.wait_for_timeout(200)

    start_button = page.locator(
        "button:has-text('Start Tournament'), button:has-text('Create Tournament')"
    ).last
    await start_button.click()
    await page.wait_for_timeout(3000)

    # Run the tournament
    await page.wait_for_selector(
        ".tournament-controls, .tournament-view", timeout=10000
    )
    run_button = page.locator(
        "button:has-text('Run Tournament'), button:has-text('Run All')"
    ).first
    await run_button.click()

    # Wait for tournament to complete (can take a while)
    # Look for completion status or progress reaching 100%
    await page.wait_for_selector(
        "[data-tournament-status='completed'], .tournament-complete", timeout=60000
    )

    # Verify results are displayed
    # Should see leaderboard or results table
    await page.wait_for_selector(
        ".leaderboard, .tournament-results, table", timeout=10000
    )

    # Check for console errors
    errors = await check_for_console_errors(page)
    assert not errors, f"Console errors during tournament run: {errors}"

    # Verify backend completion
    response = await page.evaluate("""
        async () => {
            const res = await fetch('/api/tournaments');
            return await res.json();
        }
    """)

    assert len(response) > 0, "No tournaments found"
    latest = response[0]
    assert latest["status"] == "completed", (
        f"Tournament not completed: {latest['status']}"
    )


@pytest.mark.asyncio
async def test_open_stored_tournament(page: Page, test_server: str):
    """
    Test opening a previously stored tournament.

    Steps:
    1. Ensure at least one tournament exists
    2. Navigate to Tournaments tab
    3. Click on a stored tournament
    4. Verify tournament data loads
    5. Verify leaderboard and results display
    """
    # First create a small tournament
    await page.goto(test_server, wait_until="networkidle")
    await page.wait_for_timeout(2000)

    await page.click("text=Tournaments", timeout=5000)
    await page.wait_for_timeout(1000)

    new_tournament_button = page.locator(
        "button:has-text('New Tournament'), button:has-text('Create Tournament')"
    ).first
    await new_tournament_button.click()
    await page.wait_for_timeout(1000)

    await page.wait_for_selector(".tournament-config, #tournament-form", timeout=10000)

    scenario_checkboxes = page.locator("input[type='checkbox'][data-scenario-id]")
    count = await scenario_checkboxes.count()
    if count >= 2:
        for i in range(min(2, count)):
            await scenario_checkboxes.nth(i).check()
            await page.wait_for_timeout(200)

    negotiator_checkboxes = page.locator("input[type='checkbox'][data-negotiator-type]")
    count = await negotiator_checkboxes.count()
    if count >= 2:
        for i in range(min(2, count)):
            await negotiator_checkboxes.nth(i).check()
            await page.wait_for_timeout(200)

    start_button = page.locator(
        "button:has-text('Start Tournament'), button:has-text('Create Tournament')"
    ).last
    await start_button.click()
    await page.wait_for_timeout(5000)

    # Go back to tournament list
    await page.click("text=Tournaments", timeout=5000)
    await page.wait_for_timeout(1000)

    # Click on the tournament we just created
    tournament_item = page.locator("[data-tournament-id], .tournament-item").first
    await tournament_item.click()
    await page.wait_for_timeout(2000)

    # Verify we're viewing the tournament
    await page.wait_for_selector(".tournament-view, .tournament-details", timeout=10000)

    # Check for tournament-specific elements
    await page.wait_for_selector(".tournament-controls", timeout=5000)

    # Check for console errors
    errors = await check_for_console_errors(page)
    assert not errors, f"Console errors when opening stored tournament: {errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
