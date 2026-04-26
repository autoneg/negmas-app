#!/usr/bin/env python
"""Profile a negotiation run to identify performance bottlenecks."""

import asyncio
import subprocess
import time
from pathlib import Path

from playwright.async_api import async_playwright


async def profile_negotiation():
    """Run a Camera negotiation and capture performance traces."""

    # Start the server
    server_process = subprocess.Popen(
        [".venv/bin/python", "-m", "negmas_app.main", "run"],
        cwd=Path(__file__).parent.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start - poll until ready
    import urllib.request

    print("Waiting for server to start...")
    for _ in range(30):  # Try for 30 seconds
        try:
            urllib.request.urlopen("http://127.0.0.1:8019", timeout=1)
            print("Server is ready!")
            break
        except Exception:
            await asyncio.sleep(1)
    else:
        print("Server failed to start!")
        server_process.terminate()
        return

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False
            )  # Use headed mode to see what happens
            context = await browser.new_context()

            # Enable tracing
            await context.tracing.start(screenshots=True, snapshots=True, sources=True)

            page = await context.new_page()

            # Start CDP session for performance metrics
            client = await page.context.new_cdp_session(page)
            await client.send("Performance.enable")

            # Navigate to app
            await page.goto("http://127.0.0.1:8019")
            await page.wait_for_load_state("networkidle")

            print("Page loaded, starting negotiation setup...")

            # Click "New Negotiation" button
            await page.click("text=New Negotiation")
            await asyncio.sleep(0.5)

            # Search for Camera scenario
            await page.fill('input[placeholder*="Search"]', "Camera")
            await asyncio.sleep(0.5)

            # Click on Camera scenario
            await page.click("text=Camera")
            await asyncio.sleep(0.3)

            # Click Next to go to negotiators tab
            await page.click("text=Next")
            await asyncio.sleep(0.3)

            # Click Next to go to parameters tab
            await page.click("text=Next")
            await asyncio.sleep(0.3)

            # Click Next to go to panels tab
            await page.click("text=Next")
            await asyncio.sleep(0.3)

            # Click Next to go to display tab
            await page.click("text=Next")
            await asyncio.sleep(0.3)

            # Get initial metrics
            initial_metrics = await client.send("Performance.getMetrics")
            print(
                f"Initial JS Heap: {get_metric(initial_metrics, 'JSHeapUsedSize') / 1024 / 1024:.2f} MB"
            )

            # Start the negotiation
            print("Starting negotiation...")
            start_time = time.time()
            await page.click("text=Start Negotiation")

            # Monitor during negotiation
            step_count = 0
            last_step = -1
            stall_count = 0

            while True:
                await asyncio.sleep(0.5)
                elapsed = time.time() - start_time

                # Check current step
                try:
                    step_text = await page.text_content(".step-display", timeout=1000)
                    if step_text:
                        current_step = int(
                            step_text.split("/")[0].strip().replace("Step ", "")
                        )
                        if current_step != last_step:
                            last_step = current_step
                            step_count = current_step
                            stall_count = 0

                            # Get metrics every 20 steps
                            if current_step % 20 == 0:
                                metrics = await client.send("Performance.getMetrics")
                                heap = (
                                    get_metric(metrics, "JSHeapUsedSize") / 1024 / 1024
                                )
                                nodes = get_metric(metrics, "Nodes")
                                listeners = get_metric(metrics, "JSEventListeners")
                                print(
                                    f"Step {current_step}: Heap={heap:.2f}MB, DOM Nodes={nodes}, Listeners={listeners}"
                                )
                        else:
                            stall_count += 1
                            if stall_count > 10:  # Stalled for 5 seconds
                                print(
                                    f"STALLED at step {current_step} after {elapsed:.1f}s"
                                )
                                break
                except Exception:
                    pass

                # Check if negotiation completed
                try:
                    completed = await page.query_selector("text=Agreement reached")
                    if completed:
                        print(
                            f"Negotiation completed in {elapsed:.1f}s with {step_count} steps"
                        )
                        break

                    no_agreement = await page.query_selector("text=No agreement")
                    if no_agreement:
                        print(
                            f"Negotiation ended (no agreement) in {elapsed:.1f}s with {step_count} steps"
                        )
                        break
                except Exception:
                    pass

                if elapsed > 120:  # Timeout after 2 minutes
                    print(f"TIMEOUT after {elapsed:.1f}s at step {step_count}")
                    break

            # Final metrics
            final_metrics = await client.send("Performance.getMetrics")
            print(
                f"\nFinal JS Heap: {get_metric(final_metrics, 'JSHeapUsedSize') / 1024 / 1024:.2f} MB"
            )
            print(f"Final DOM Nodes: {get_metric(final_metrics, 'Nodes')}")
            print(
                f"Final Event Listeners: {get_metric(final_metrics, 'JSEventListeners')}"
            )

            # Stop tracing and save
            await context.tracing.stop(path="negotiation_trace.zip")
            print("\nTrace saved to negotiation_trace.zip")
            print("Open with: npx playwright show-trace negotiation_trace.zip")

            await browser.close()

    finally:
        server_process.terminate()
        server_process.wait()


def get_metric(metrics_response, name):
    """Extract a metric value by name."""
    for m in metrics_response.get("metrics", []):
        if m["name"] == name:
            return m["value"]
    return 0


if __name__ == "__main__":
    asyncio.run(profile_negotiation())
