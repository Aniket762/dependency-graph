# Generated CSS from LLM
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
#MainMenu, footer, header  { visibility: hidden; }
.block-container           { padding-top: 2rem; max-width: 1100px; }

/* ── Landing cards ── */
.platform-card {
    background: #111;
    border: 2px solid #2a2a2a;
    border-radius: 18px;
    padding: 48px 24px 40px;
    text-align: center;
    min-height: 220px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 14px;
    cursor: pointer;
    transition: border-color .2s, box-shadow .2s, transform .15s;
}
.platform-card:hover {
    border-color: #555;
    transform: translateY(-3px);
    box-shadow: 0 10px 36px rgba(0,0,0,0.5);
}
.card-name {
    font-size: 18px; font-weight: 600;
    color: #fff; letter-spacing: .3px;
}
.card-sub { font-size: 12px; color: #777; line-height: 1.5; }

/* Invisible Streamlit button overlaid on card */
div[data-testid="column"] .stButton > button {
    position: absolute !important;
    top: 0 !important; left: 0 !important;
    width: 100% !important; height: 100% !important;
    opacity: 0 !important;
    cursor: pointer !important;
    z-index: 10 !important;
}
div[data-testid="column"] { position: relative; }

/* ── Example pills ── */
.stButton.pill-btn > button,
div[data-testid="column"] .stButton.pill-btn > button {
    all: unset !important;
    display: block !important;
    width: 100% !important; height: auto !important;
    opacity: 1 !important; position: static !important;
    background: #f1f5f9 !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 20px !important;
    padding: 6px 12px !important;
    font-size: 12px !important;
    color: #475569 !important;
    cursor: pointer !important;
    text-align: center !important;
    transition: background .15s !important;
}
.stButton.pill-btn > button:hover {
    background: #e2e8f0 !important;
}

/* ── Result chips ── */
.chip {
    display: inline-block;
    background: #f0fdf4; border: 1px solid #bbf7d0;
    color: #166534; border-radius: 8px;
    padding: 4px 12px; font-size: 13px;
    font-weight: 500; margin: 3px;
}
.chain-box {
    background: #0f172a; color: #e2e8f0;
    border-radius: 10px; padding: 14px 20px;
    font-family: monospace; font-size: 13px;
    line-height: 2; overflow-x: auto; margin-bottom: 8px;
}
.badge {
    display: inline-block; border-radius: 6px;
    padding: 3px 9px; font-size: 11px;
    font-weight: 600; margin: 2px;
}
.badge-user     { background:#dbeafe; color:#1e40af; }
.badge-chain    { background:#fef3c7; color:#92400e; }
.badge-produces { background:#dcfce7; color:#166534; }
.badge-warn     { background:#fee2e2; color:#991b1b; }
</style>
"""

GITHUB_SVG = """<svg width="52" height="52" viewBox="0 0 98 96" xmlns="http://www.w3.org/2000/svg">
  <path fill-rule="evenodd" clip-rule="evenodd" fill="#ffffff"
    d="M48.854 0C21.839 0 0 22 0 49.217c0 21.756 13.993 40.172 33.405 46.69
    2.427.49 3.316-1.059 3.316-2.362 0-1.141-.08-5.052-.08-9.127
    -13.59 2.934-16.42-5.867-16.42-5.867-2.184-5.704-5.42-7.17-5.42-7.17
    -4.448-3.015.324-3.015.324-3.015 4.934.326 7.523 5.052 7.523 5.052
    4.367 7.496 11.404 5.378 14.235 4.074.404-3.178 1.699-5.378 3.074-6.6
    -10.839-1.141-22.243-5.378-22.243-24.283 0-5.378 1.94-9.778 5.014-13.2
    -.485-1.222-2.184-6.275.486-13.038 0 0 4.125-1.304 13.426 5.052
    a46.97 46.97 0 0 1 12.214-1.63c4.125 0 8.33.571 12.213 1.63
    9.302-6.356 13.427-5.052 13.427-5.052 2.67 6.763.97 11.816.485 13.038
    3.155 3.422 5.015 7.822 5.015 13.2 0 18.905-11.404 23.06-22.324 24.283
    1.78 1.548 3.316 4.481 3.316 9.126 0 6.6-.08 11.897-.08 13.526
    0 1.304.89 2.853 3.316 2.364 19.412-6.52 33.405-24.935 33.405-46.691
    C97.707 22 75.788 0 48.854 0z"/>
</svg>"""

GOOGLE_SVG = """<svg width="52" height="52" viewBox="0 0 533.5 544.3" xmlns="http://www.w3.org/2000/svg">
  <path d="M533.5 278.4c0-18.5-1.5-37.1-4.7-55.3H272.1v104.8h147c-6.1 33.8-25.7 63.7-54.4 82.7v68h87.7c51.5-47.4 81.1-117.4 81.1-200.2z" fill="#4285f4"/>
  <path d="M272.1 544.3c73.4 0 135.3-24.1 180.4-65.7l-87.7-68c-24.4 16.6-55.9 26-92.6 26-71 0-131.2-47.9-152.8-112.3H28.9v70.1c46.2 91.9 140.3 149.9 243.2 149.9z" fill="#34a853"/>
  <path d="M119.3 324.3c-11.4-33.8-11.4-70.4 0-104.2V150H28.9c-38.6 76.9-38.6 167.5 0 244.4l90.4-70.1z" fill="#fbbc04"/>
  <path d="M272.1 107.7c38.8-.6 76.3 14 104.4 40.8l77.7-77.7C405 24.6 339.7-.8 272.1 0 169.2 0 75.1 58 28.9 150l90.4 70.1c21.5-64.5 81.8-112.4 152.8-112.4z" fill="#ea4335"/>
</svg>"""