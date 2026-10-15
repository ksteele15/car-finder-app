"""One-time: log into Facebook in a real browser window and save the session to fb_state.json."""
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=False)
    ctx = b.new_context()
    ctx.new_page().goto("https://www.facebook.com/login")
    input("Log in (use a throwaway/secondary account), then press Enter here... ")
    ctx.storage_state(path="fb_state.json")
    b.close()
print("saved fb_state.json")
