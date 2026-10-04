"""Record an animated SVG walkthrough of the Streamlit demo (demo mode,
no API key). Frames: app loaded -> monthly revenue results -> SQL shown
-> top products bar chart. Output: assets/demo.svg"""
import base64
import io
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright  # noqa: E402

PORT = 8502
W, H = 1200, 750
FRAMES = []


def shot(page, name):
    png = page.screenshot()
    FRAMES.append((name, png))
    print("frame:", name, len(png) // 1024, "KB")


def pick_question(page, option_text):
    box = page.locator('[data-testid="stSelectbox"]')
    box.scroll_into_view_if_needed()
    box.click()
    page.get_by_role("option", name=option_text).click()
    time.sleep(1)


def main():
    env = dict(os.environ, PATH=os.path.dirname(sys.executable)
               + os.pathsep + os.environ["PATH"])
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         "--server.headless", "true", "--server.port", str(PORT),
         "--browser.gatherUsageStats", "false"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # wait for streamlit to listen
        import socket
        for _ in range(60):
            s = socket.socket()
            try:
                s.connect(("localhost", PORT))
                s.close()
                break
            except OSError:
                time.sleep(1)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": W, "height": H})
            page.goto(f"http://localhost:{PORT}", wait_until="networkidle")
            page.get_by_role("button", name="Analyser").wait_for(timeout=60000)
            time.sleep(2)

            # frame 1: pick the monthly-revenue question
            pick_question(page, "Quel est le chiffre d'affaires par mois en 2024 ?")
            shot(page, "question-selected")

            # frame 2: run it, show insight + line chart
            page.get_by_role("button", name="Analyser").click()
            page.get_by_text("Réponse").wait_for(timeout=60000)
            # plotly.js is heavy: wait for the chart to actually render
            page.locator(".js-plotly-plot").first.wait_for(timeout=45000)
            time.sleep(2)
            shot(page, "monthly-results")

            # frame 3: open the SQL expander for auditability
            page.get_by_text("Voir le SQL généré").click()
            time.sleep(1)
            shot(page, "sql-visible")

            # frame 4: second question -> bar chart
            try:
                pick_question(page, "Quels sont les 5 produits les plus vendus en quantité ?")
                page.get_by_role("button", name="Analyser").click()
                page.locator(".js-plotly-plot").first.wait_for(timeout=45000)
                time.sleep(2)
                shot(page, "top-products")
            except Exception as e:
                print("frame 4 skipped:", e)
            browser.close()
    finally:
        proc.terminate()

    # assemble animated SVG (JPEG frames, hard cuts via SMIL discrete)
    from PIL import Image
    n = len(FRAMES)
    dur = n * 3
    parts = [f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
             'xmlns="http://www.w3.org/2000/svg" '
             'xmlns:xlink="http://www.w3.org/1999/xlink">']
    for i, (name, png) in enumerate(FRAMES):
        img = Image.open(io.BytesIO(png)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=72)
        b64 = base64.b64encode(buf.getvalue()).decode()
        start, end = i / n, (i + 1) / n
        parts.append(
            f'<image x="0" y="0" width="{W}" height="{H}" '
            f'xlink:href="data:image/jpeg;base64,{b64}" opacity="0">'
            f'<animate attributeName="opacity" values="0;1;0" '
            f'keyTimes="0;{start:.4f};{end:.4f}" calcMode="discrete" '
            f'dur="{dur}s" repeatCount="indefinite"/></image>')
    parts.append("</svg>")
    out = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "assets", "demo.svg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write("\n".join(parts))
    print("wrote", out, os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    main()
