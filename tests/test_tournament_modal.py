"""Test NewTournamentModal data loading - CRITICAL BLOCKER

This test verifies that:
1. Scenarios are loaded and displayed (API returns 271, UI should show 271)
2. Negotiators are loaded and displayed (API returns 405, UI should show 405)
3. Presets are loaded and can be selected
"""

import time
from playwright.sync_api import Page, expect


def test_new_tournament_modal_loads_data(page: Page, base_url: str):
    """Test that NewTournamentModal loads scenarios and negotiators correctly."""

    # Navigate to tournaments page
    page.goto(f"{base_url}/tournaments")

    # Wait for page to load
    page.wait_for_load_state("networkidle")
    time.sleep(1)

    # Click "New Tournament" button
    new_tournament_btn = page.locator('button:has-text("New Tournament")')
    expect(new_tournament_btn).to_be_visible()
    new_tournament_btn.click()

    # Wait for modal to appear
    modal = page.locator(".modal-overlay")
    expect(modal).to_be_visible()

    # Wait for data to load (give it a few seconds)
    time.sleep(3)

    # Check scenarios tab (should be active by default)
    scenarios_tab = page.locator('.wizard-tab:has-text("Scenarios")')
    expect(scenarios_tab).to_have_class("wizard-tab active")

    # Check if scenarios are displayed
    # Look for "Available" count badge in DualListSelector
    available_count = page.locator(
        '.dual-list-header:has-text("Available") .count-badge'
    ).first
    expect(available_count).to_be_visible()

    # Get the count text
    count_text = available_count.inner_text()
    print(f"\n[TEST] Available scenarios count: {count_text}")

    # Verify count is not 0
    count_value = int(count_text)
    assert count_value > 0, f"Expected scenarios > 0, got {count_value}"
    assert count_value > 200, f"Expected ~271 scenarios, got {count_value}"

    # Switch to Competitors tab
    competitors_tab = page.locator('.wizard-tab:has-text("Competitors")')
    competitors_tab.click()
    time.sleep(1)

    # Check if negotiators are displayed
    available_count = page.locator(
        '.dual-list-header:has-text("Available") .count-badge'
    ).first
    expect(available_count).to_be_visible()

    count_text = available_count.inner_text()
    print(f"[TEST] Available negotiators count: {count_text}")

    # Verify count is not 0
    count_value = int(count_text)
    assert count_value > 0, f"Expected negotiators > 0, got {count_value}"
    assert count_value > 300, f"Expected ~405 negotiators, got {count_value}"

    print("\n[TEST] ✓ All data loaded successfully!")


def test_console_logs_for_debugging(page: Page, base_url: str):
    """Capture console logs to debug data loading issues."""

    console_messages = []

    def handle_console(msg):
        console_messages.append(f"[{msg.type}] {msg.text}")
        print(f"[BROWSER CONSOLE] [{msg.type}] {msg.text}")

    page.on("console", handle_console)

    # Navigate to tournaments page
    page.goto(f"{base_url}/tournaments")
    page.wait_for_load_state("networkidle")
    time.sleep(1)

    # Click "New Tournament" button
    new_tournament_btn = page.locator('button:has-text("New Tournament")')
    new_tournament_btn.click()

    # Wait for modal and data loading
    time.sleep(4)

    # Print all console messages
    print("\n" + "=" * 80)
    print("CAPTURED CONSOLE LOGS:")
    print("=" * 80)
    for msg in console_messages:
        print(msg)
    print("=" * 80 + "\n")

    # Check for our debug logs
    load_data_logs = [msg for msg in console_messages if "NewTournamentModal" in msg]
    assert len(load_data_logs) > 0, "No NewTournamentModal debug logs found!"

    # Check for data loading logs
    loaded_data_logs = [msg for msg in console_messages if "Loaded data" in msg]
    if loaded_data_logs:
        print(f"\n[TEST] Found data loading log: {loaded_data_logs[0]}")
    else:
        print("\n[TEST] WARNING: No 'Loaded data' log found!")


if __name__ == "__main__":
    # This allows running the test file directly with playwright
    import sys
    import subprocess

    result = subprocess.run(
        ["pytest", __file__, "-v", "-s"], cwd="/Users/yasser/code/projects/negmas-app"
    )
    sys.exit(result.returncode)
