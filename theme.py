"""Central theme for the Streamlit app.

Edit the variables in the SETTINGS section to restyle the whole site.
Colours were sampled from the Cafe Gray / Wishbone reference image.
"""

import streamlit as st

# ---------------------------------------------------------------- SETTINGS --
# Colours
COLOR_BACKGROUND = "#EFE9DB"   # cream paper (main page)
COLOR_SURFACE = "#E4DCC8"      # slightly darker cream (sidebar, cards, inputs)
COLOR_PRIMARY = "#C93A40"      # red from the coffee-cup logo (buttons, accents)
COLOR_ACCENT = "#8DBBC7"       # dusty blue from the border pattern
COLOR_TEXT = "#5A5A5A"         # warm grey body text
COLOR_HEADING = "#444444"      # darker grey for titles
COLOR_ON_PRIMARY = "#EFE9DB"   # text colour used on top of the red

# Typography
FONT_NAME = "Poppins"
FONT_WEIGHTS = "400;500;600"   # weights to download from Google Fonts
FONT_FAMILY = f"'{FONT_NAME}', sans-serif"
NAV_FONT_SIZE = "1.2rem"       # sidebar navigation (default is about 1rem)
# FONT_FAMILY = "'Poppins', Georgia, 'Times New Roman', serif"

# Shape
BORDER_WIDTH = "2px"
BORDER_RADIUS = "6px"
# -----------------------------------------------------------------------------


def _css():
    return f"""
    <style>

    @import url('https://fonts.googleapis.com/css2?family={FONT_NAME}:wght@{FONT_WEIGHTS}&display=swap');

    :root {{
        --bg: {COLOR_BACKGROUND};
        --surface: {COLOR_SURFACE};
        --primary: {COLOR_PRIMARY};
        --accent: {COLOR_ACCENT};
        --text: {COLOR_TEXT};
        --heading: {COLOR_HEADING};
        --on-primary: {COLOR_ON_PRIMARY};
        --font: {FONT_FAMILY};
        --border-width: {BORDER_WIDTH};
        --radius: {BORDER_RADIUS};
    }}

    /* Page + text */
    .stApp, [data-testid="stHeader"] {{
        background-color: var(--bg);
        color: var(--text);
        font-family: var(--font);
    }}
    h1, h2, h3, h4, h5, h6 {{
        color: var(--heading) !important;
        font-family: var(--font) !important;
    }}
    h1 {{
        border-bottom: var(--border-width) solid var(--accent);
        padding-bottom: 0.3rem;
    }}
    a {{ color: var(--primary) !important; }}
    hr {{ border-color: var(--accent) !important; }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: var(--surface);
        border-right: var(--border-width) solid var(--accent);
    }}

    [data-testid="stSidebar"] [data-testid="stRadio"] label p {{
        font-size: {NAV_FONT_SIZE};
    }}

    /* Buttons */
    .stButton > button, .stDownloadButton > button,
    [data-testid="stFormSubmitButton"] > button {{
        background-color: var(--primary);
        color: var(--on-primary);
        border: var(--border-width) solid var(--primary);
        border-radius: var(--radius);
        font-family: var(--font);
    }}
    .stButton > button:hover, .stDownloadButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {{
        background-color: var(--bg);
        color: var(--primary);
        border-color: var(--primary);
    }}

    /* Inputs */
    .stTextInput input, .stNumberInput input,
    [data-baseweb="select"] > div {{
        background-color: var(--surface) !important;
        color: var(--text) !important;
        border: var(--border-width) solid var(--accent) !important;
        border-radius: var(--radius) !important;
    }}

    /* File uploader: keep button text on one line and let the button grow */
    [data-testid="stFileUploaderDropzone"] button {{
        white-space: nowrap;
        width: auto;
        min-width: max-content;
        padding: 0.4rem 1.2rem;
    }}

    /* Forms, metrics, alerts */
    [data-testid="stForm"], [data-testid="stMetric"] {{
        background-color: var(--surface);
        border: var(--border-width) solid var(--accent);
        border-radius: var(--radius);
        padding: 1rem;
    }}
    [data-testid="stMetricValue"] {{ color: var(--primary); }}
    [data-testid="stAlert"] {{
        background-color: var(--surface);
        border: var(--border-width) solid var(--accent);
        border-radius: var(--radius);
        color: var(--text);
    }}

    /* Progress bar */
    [data-testid="stProgress"] > div > div > div > div {{
        background-color: var(--primary);
    }}
    </style>
    """


def apply_theme():
    """Call once at the start of main(), after st.set_page_config()."""
    st.markdown(_css(), unsafe_allow_html=True)