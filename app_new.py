import hashlib
import html
import io
import numbers
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.cleaning import clean_data
from src.executor import execute_analysis
from src.insights import generate_executive_summary
from src.export import create_excel_export

# The AI step needs a Groq API key. If it is missing (or the groq package is
# not installed), cleaning, the summary and the Excel export still work and
# the Ask tab explains what to do instead of the whole app crashing.
try:
    from src.llm import generate_analysis_code
    AI_SETUP_ERROR = None
except Exception as setup_error:
    generate_analysis_code = None
    AI_SETUP_ERROR = str(setup_error)


# Files with more rows than this get a heads-up, and the Excel export is
# only built when asked for.
LARGE_ROWS = 200_000
EAGER_EXCEL_ROWS = 50_000

SAMPLE_NAME = "sample_sales_data.csv"


# ============================================================
# Page configuration
# ============================================================

st.set_page_config(
    page_title="AI Data Analysis",
    page_icon="📊",
    layout="wide",
)


# ============================================================
# Streamlit version helpers
# ============================================================

def _version_tuple():
    parts = []
    for piece in st.__version__.split(".")[:2]:
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


# Newer Streamlit replaced use_container_width with width="stretch".
STRETCH = (
    {"width": "stretch"}
    if _version_tuple() >= (1, 50)
    else {"use_container_width": True}
)


def keyed_container(key, **kwargs):
    """Container with a CSS hook (older Streamlit has no key=)."""
    try:
        return st.container(key=key, **kwargs)
    except TypeError:
        return st.container(**kwargs)


# ============================================================
# Styling: aurora background, glass cards, shimmer buttons
# ============================================================

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=Hanken+Grotesk:wght@400;500;600&family=Fira+Code:wght@400;500&display=swap');

:root{
  --ink:#0A0E1F;
  --glass:rgba(255,255,255,.045);
  --glass-2:rgba(255,255,255,.075);
  --line:rgba(255,255,255,.11);
  --txt:#E9ECFF;
  --muted:#9AA3C7;
  --violet:#8B7CFF;
  --teal:#3EE6C3;
  --pink:#FF6FB5;
  --amber:#FFC857;
  --display:'Bricolage Grotesque','Hanken Grotesk',system-ui,sans-serif;
  --body:'Hanken Grotesk',system-ui,-apple-system,'Segoe UI',sans-serif;
}

@property --n{syntax:'<integer>';initial-value:0;inherits:false}

/* ---------- canvas ---------- */
.stApp{background:var(--ink);color:var(--txt)}
.stApp,.stApp p,.stApp label,.stApp li,.stApp button,.stApp input,.stApp textarea,.stApp [data-testid="stMarkdownContainer"]{font-family:var(--body) !important}
[data-testid="stAppViewContainer"],[data-testid="stMain"],.main{
  background:transparent !important;position:relative;z-index:1}
[data-testid="stHeader"]{background:transparent !important}
.stApp::before{
  content:"";position:fixed;inset:-25%;z-index:0;pointer-events:none;
  background:
    radial-gradient(38% 34% at 22% 28%,rgba(139,124,255,.42),transparent 70%),
    radial-gradient(32% 30% at 78% 16%,rgba(62,230,195,.26),transparent 70%),
    radial-gradient(36% 32% at 62% 84%,rgba(255,111,181,.20),transparent 70%);
}
.stApp::after{
  content:"";position:fixed;inset:0;z-index:3;pointer-events:none;opacity:.06;
  mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
}
.block-container{padding-top:2.4rem !important;padding-bottom:5rem !important;max-width:1180px}
#MainMenu,footer{visibility:hidden}
::selection{background:rgba(139,124,255,.45)}
span[data-testid="stIconMaterial"]{font-family:"Material Symbols Rounded" !important}

.stApp p,.stApp li,.stApp label,.stApp div[data-testid="stMarkdownContainer"]{color:var(--txt)}
h1,h2,h3,h4,h5{font-family:var(--display) !important;letter-spacing:-.02em;color:#fff !important}

/* ---------- hero ---------- */
.hero-title{
  font-family:var(--display);font-weight:700;margin:.2rem 0 1rem;
  font-size:clamp(2.5rem,5.4vw,4.5rem);line-height:1.0;letter-spacing:-.035em;
  background:linear-gradient(100deg,#F1EFFF 0%,#B7A9FF 22%,#3EE6C3 48%,#B7A9FF 74%,#F1EFFF 100%);
  background-size:260% 100%;-webkit-background-clip:text;background-clip:text;
  -webkit-text-fill-color:transparent;color:transparent;
}
.hero-title.compact{font-size:clamp(1.9rem,3.4vw,2.8rem);line-height:1.05}
.hero-sub{color:var(--muted) !important;font-size:1.08rem;line-height:1.55;max-width:46ch;margin:0 0 1.4rem}

/* ---------- uploader ---------- */
[data-testid="stFileUploaderDropzone"]{
  background:var(--glass);border:1.5px dashed rgba(139,124,255,.55);border-radius:22px;
  padding:1.5rem 1.4rem;transition:border-color .2s,background .2s}
[data-testid="stFileUploaderDropzone"]:hover{border-color:var(--teal);background:rgba(62,230,195,.06)}
[data-testid="stFileUploaderDropzone"] *{color:var(--muted)}
[data-testid="stFileUploaderFile"]{border-radius:14px}

/* ---------- stepper ---------- */
.steps{display:flex;align-items:center;margin:1.6rem 0 1.4rem;flex-wrap:wrap;row-gap:.8rem}
.step{display:flex;align-items:center;gap:.65rem}
.step .dot{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;
  font-size:.82rem;font-weight:700;border:1.5px solid var(--line);color:var(--muted);
  background:rgba(255,255,255,.03);flex:none}
.step.done .dot{background:linear-gradient(135deg,var(--violet),var(--teal));border:0;color:#06101c}
.step.now .dot{border-color:var(--teal);color:var(--teal);box-shadow:0 0 0 5px rgba(62,230,195,.13)}
.step .t b{display:block;font-weight:600;font-size:.95rem;color:#fff}
.step .t small{display:block;color:var(--muted);font-size:.78rem;margin-top:1px}
.link{flex:1 1 28px;min-width:28px;height:2px;margin:0 .9rem;background:var(--line);border-radius:2px}
.link.done{background:linear-gradient(90deg,var(--violet),var(--teal))}

/* ---------- glass + bento ---------- */
.glass,[class*="st-key-glass"]{
  background:var(--glass);border:1px solid var(--line);border-radius:22px;
  padding:1.25rem 1.4rem;backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)}
.lab{color:var(--muted);font-size:.88rem;font-weight:500;margin-bottom:.3rem}
.num{font-family:var(--display);font-weight:700;font-size:2.4rem;line-height:1.05;color:#fff;letter-spacing:-.03em;font-variant-numeric:tabular-nums}
.num.xl{font-size:clamp(3.4rem,7vw,5.6rem);letter-spacing:-.045em}
.sub{color:var(--muted);font-size:.9rem;line-height:1.45;margin-top:.55rem}

.bento{display:grid;grid-template-columns:1.5fr 1fr 1fr;grid-template-rows:auto auto;gap:14px;margin:.4rem 0 1.6rem}
.cell{background:var(--glass);border:1px solid var(--line);border-radius:18px;padding:1.15rem 1.3rem;backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)}
.cell.main{grid-row:span 2;border-radius:30px;padding:1.6rem 1.7rem;
  background:linear-gradient(160deg,rgba(139,124,255,.20),rgba(62,230,195,.07) 70%),var(--glass);
  border-color:rgba(139,124,255,.35);display:flex;flex-direction:column;justify-content:space-between}
.cell.wide{grid-column:span 2}
.meter{height:8px;border-radius:99px;background:rgba(255,255,255,.09);overflow:hidden;margin-top:1.1rem}
.meter i{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,var(--violet),var(--teal))}

/* ticking numbers (CSS only; formatted value appears when the count ends) */
.tick{display:inline-grid}
.tick>span{grid-area:1/1}
.tick .cnt{counter-reset:n var(--n);opacity:0}
.tick .cnt::after{content:counter(n)}
.tick .fin{opacity:1}
@media (prefers-reduced-motion:no-preference){
  .tick .cnt{opacity:1;animation:tick 1.2s cubic-bezier(.2,.7,.2,1) both,vanish 0s 1.2s forwards}
  .tick .fin{opacity:0;animation:appear 0s 1.2s forwards}
  .hero-title{animation:flow 10s linear infinite}
  .stApp::before{animation:aurora 30s ease-in-out infinite alternate}
}
@keyframes tick{from{--n:0}to{--n:var(--t)}}
@keyframes vanish{to{opacity:0}}
@keyframes appear{to{opacity:1}}
@keyframes flow{to{background-position:-260% 0}}
@keyframes aurora{
  from{transform:translate3d(-3%,-2%,0) rotate(0deg) scale(1)}
  to{transform:translate3d(4%,3%,0) rotate(8deg) scale(1.12)}}

/* ---------- cleaning tab ---------- */
.flowbar{display:flex;height:16px;border-radius:99px;overflow:hidden;background:rgba(255,255,255,.08);gap:2px}
.flowbar i{display:block;height:100%}
.flowbar .k{background:linear-gradient(90deg,var(--violet),var(--teal))}
.flowbar .d{background:var(--pink)}
.flowbar .e{background:var(--amber)}
.flowbar .o{background:#7B86B8}
.legend{display:flex;flex-wrap:wrap;gap:.5rem 1.4rem;margin-top:.9rem;color:var(--muted);font-size:.9rem}
.legend b{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:.45rem}
.legend strong{color:#fff;font-weight:600;margin-left:.15rem}
.strip{display:grid;grid-template-columns:repeat(4,1fr);margin:1rem 0 1.4rem;
  background:var(--glass);border:1px solid var(--line);border-radius:20px;overflow:hidden}
.strip>div{padding:1.1rem 1.3rem;border-left:1px solid var(--line)}
.strip>div:first-child{border-left:0}
.strip .num{font-size:1.9rem}
.timeline{position:relative;margin:.4rem 0 0;padding-left:1.7rem}
.timeline::before{content:"";position:absolute;left:7px;top:6px;bottom:6px;width:2px;background:var(--line)}
.tl{position:relative;padding:.35rem 0 .9rem;color:var(--txt);font-size:.98rem}
.tl::before{content:"";position:absolute;left:-1.7rem;top:.5rem;width:16px;height:16px;border-radius:50%;
  background:var(--ink);border:2px solid var(--teal)}
.tl.idle{color:var(--muted)}
.tl.idle::before{border-color:#4a5380}
.tl.warn::before{border-color:var(--amber)}
.tl strong{color:#fff;font-weight:600}

/* ---------- summary tab ---------- */
.insight{background:var(--glass);border:1px solid var(--line);border-left:3px solid var(--teal);
  border-radius:6px 18px 18px 6px;padding:.95rem 1.2rem;margin-bottom:.7rem;line-height:1.55;color:var(--txt)}
.insight code,.answer code{background:rgba(255,255,255,.1);border-radius:6px;padding:.1rem .35rem;font-family:'Fira Code',monospace;font-size:.88em}
.reco{position:relative;border-radius:24px;padding:1.5rem 1.6rem;margin-top:1.1rem;
  background:linear-gradient(150deg,rgba(139,124,255,.22),rgba(255,111,181,.10));
  border:1px solid rgba(139,124,255,.5);box-shadow:0 0 60px -18px rgba(139,124,255,.7)}
.reco h4{margin:0 0 .5rem !important;font-size:1.25rem !important}
.reco p{margin:0;line-height:1.6;color:var(--txt)}

/* ---------- ask tab ---------- */
.answer{background:linear-gradient(160deg,rgba(62,230,195,.12),rgba(139,124,255,.10));
  border:1px solid rgba(62,230,195,.35);border-radius:22px;padding:1.2rem 1.5rem;margin:.3rem 0 .6rem}
.answer .num{font-size:clamp(2.2rem,4.4vw,3.4rem)}
.answer .num.text{font-size:1.5rem;line-height:1.3;letter-spacing:-.01em}
.kvgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:.3rem 0 .6rem}
.kv{background:var(--glass);border:1px solid var(--line);border-radius:16px;padding:.9rem 1.1rem}
.kv .num{font-size:1.6rem}
.tag{display:inline-block;font-size:.82rem;font-weight:500;color:#06101c;background:var(--amber);border-radius:99px;padding:.18rem .7rem;margin-bottom:.6rem}
.errbox{border:1px solid rgba(255,111,181,.5);background:rgba(255,111,181,.08);border-radius:18px;padding:1.1rem 1.3rem;line-height:1.55}
.errbox b{color:#fff;font-size:1.05rem}
.empty{color:var(--muted);padding:.8rem 0 .4rem;font-size:1rem}
.notebox{border:1px solid rgba(255,200,87,.5);background:rgba(255,200,87,.08);border-radius:18px;padding:1rem 1.3rem;line-height:1.55;margin:.4rem 0 1rem}
.notebox b{color:#fff}
.notebox code{background:rgba(255,255,255,.1);border-radius:6px;padding:.1rem .35rem;font-family:'Fira Code',monospace;font-size:.88em}
.tag.soft{background:rgba(255,255,255,.12);color:var(--txt);margin:0 0 .4rem}
.stApp p.samplehint{color:var(--muted);font-size:.9rem;margin:.2rem 0 0}
[data-testid="stAppDeployButton"],.stDeployButton{display:none !important}

/* chips: suggestion buttons laid out as a wrapping row */
.st-key-chips{flex-direction:row !important;flex-wrap:wrap;gap:.5rem !important;margin-bottom:.6rem}
.st-key-chips [data-testid="stElementContainer"]{width:auto !important;flex:0 0 auto}
.st-key-chips button{border-radius:99px !important;padding:.3rem .95rem !important;min-height:0 !important}
.st-key-chips button p{font-size:.88rem !important}

/* ---------- widgets ---------- */
div[data-baseweb="input"],div[data-baseweb="base-input"]{
  background:rgba(255,255,255,.05) !important;border-radius:14px !important;border-color:var(--line) !important}
div[data-baseweb="input"]:focus-within{border-color:var(--teal) !important;box-shadow:0 0 0 3px rgba(62,230,195,.18)}
div[data-baseweb="input"] input{color:#fff !important;font-size:1.02rem;padding:.8rem .9rem !important}
[data-testid="stForm"]{border:0 !important;padding:0 !important;background:transparent !important}
.st-key-askwrap [data-testid="stHorizontalBlock"]{align-items:center}

button[data-testid^="stBaseButton-primary"]{
  position:relative;overflow:hidden;border:0 !important;border-radius:99px !important;
  color:#06101c !important;font-weight:600;padding:.55rem 1.5rem !important;
  background:linear-gradient(100deg,#8B7CFF,#3EE6C3) !important;
  box-shadow:0 8px 26px -10px rgba(139,124,255,.9)}
button[data-testid^="stBaseButton-primary"] p{color:#06101c !important;font-weight:600}
button[data-testid^="stBaseButton-primary"]::after{
  content:"";position:absolute;inset:0;pointer-events:none;
  background:linear-gradient(110deg,transparent 30%,rgba(255,255,255,.6) 50%,transparent 70%);
  transform:translateX(-130%)}
button[data-testid^="stBaseButton-primary"]:hover::after{transform:translateX(130%);transition:transform .7s ease}
button[data-testid^="stBaseButton-primary"]:hover{filter:brightness(1.06)}
button[data-testid="stBaseButton-secondary"],button[data-testid="stBaseButton-secondaryFormSubmit"]{
  background:var(--glass) !important;border:1px solid var(--line) !important;border-radius:99px !important;color:var(--txt) !important}
button[data-testid="stBaseButton-secondary"]:hover{border-color:var(--teal) !important;color:#fff !important;box-shadow:0 0 0 3px rgba(62,230,195,.14)}
@media (prefers-reduced-motion:no-preference){
  .st-key-askwrap button[data-testid^="stBaseButton-primary"]::after{animation:idlesheen 6s ease-in-out infinite}
  @keyframes idlesheen{0%,70%{transform:translateX(-130%)}100%{transform:translateX(130%)}}
}

.stTabs [data-baseweb="tab-list"],.stTabs [role="tablist"]{gap:6px;border-bottom:1px solid var(--line)}
.stTabs [data-baseweb="tab"],.stTabs [data-testid="stTab"]{height:50px;padding:0 1.15rem;color:var(--muted);background:transparent}
.stTabs [data-baseweb="tab"] p,.stTabs [data-testid="stTab"] p{
  font-family:var(--display) !important;font-weight:600 !important;font-size:1.08rem !important;color:inherit !important}
.stTabs [aria-selected="true"]{color:#fff !important}
.stTabs [data-baseweb="tab-highlight"],.stTabs .react-aria-SelectionIndicator{
  background:linear-gradient(90deg,var(--violet),var(--teal)) !important;height:3px !important;border-radius:3px}
.stTabs [data-baseweb="tab-border"]{display:none}

[data-testid="stExpander"] details{background:var(--glass);border:1px solid var(--line) !important;border-radius:16px}
[data-testid="stAlert"]{border-radius:16px}
[data-testid="stDataFrame"]{border-radius:16px;overflow:hidden;border:1px solid var(--line)}
[data-testid="stCode"],[data-testid="stCode"] pre{border-radius:14px;font-family:'Fira Code',monospace !important}

[data-testid="stChatMessage"]{background:transparent !important;padding:.35rem 0;gap:.9rem;justify-content:flex-start !important}
[data-testid="stChatMessage"]>div:first-child,[data-testid^="stChatMessageAvatar"]{
  background:linear-gradient(135deg,var(--violet),var(--teal)) !important;border-radius:50% !important;
  width:2.2rem;height:2.2rem;min-width:2.2rem;display:grid;place-items:center;font-size:1.05rem}
[data-testid="stChatMessageContent"][aria-label^="Chat message from user"]{
  background:rgba(139,124,255,.15);border:1px solid rgba(139,124,255,.38);border-radius:18px 18px 18px 6px;
  padding:.7rem 1.05rem;flex:0 0 auto !important;width:fit-content !important;max-width:calc(100% - 3.4rem);margin-left:0 !important;margin-right:auto !important}
[data-testid="stChatMessageContent"][aria-label^="Chat message from assistant"]{
  background:var(--glass);border:1px solid var(--line);border-radius:6px 24px 24px 24px;padding:1.1rem 1.3rem}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] button[data-testid^="stBaseButton-primary"]{padding:.5rem .8rem !important;width:100%}
[data-testid="stSidebar"] button[data-testid^="stBaseButton-primary"] p{font-size:.86rem !important;white-space:nowrap}
[data-testid="stSidebar"]{background:rgba(10,14,31,.78) !important;border-right:1px solid var(--line);
  backdrop-filter:blur(18px);-webkit-backdrop-filter:blur(18px)}
[data-testid="stSidebar"]>div{background:transparent !important}
.brand{display:flex;align-items:center;gap:.7rem;margin:.2rem 0 1.4rem;font-family:var(--display);font-weight:700;font-size:1.15rem;color:#fff}
.orb{width:26px;height:26px;border-radius:50%;
  background:conic-gradient(from 200deg,#8B7CFF,#3EE6C3,#FF6FB5,#8B7CFF);box-shadow:0 0 22px rgba(139,124,255,.7)}
.fcard{background:var(--glass);border:1px solid var(--line);border-radius:16px;padding:.9rem 1rem;margin-bottom:1rem}
.fcard .fname{color:#fff;font-weight:600;word-break:break-all}
.fcard .fmeta{color:var(--muted);font-size:.86rem;margin-top:.25rem}
.howto{color:var(--muted);font-size:.93rem;line-height:1.6}
.howto b{color:#fff;font-weight:600}

/* ---------- landing preview + dtype mix ---------- */
.demo{display:flex;flex-direction:column;gap:.9rem}
.demo .bq{align-self:flex-start;background:rgba(139,124,255,.15);border:1px solid rgba(139,124,255,.38);
  border-radius:18px 18px 18px 6px;padding:.65rem 1rem;color:#fff}
.demo .ba{background:var(--glass);border:1px solid var(--line);border-radius:6px 24px 24px 24px;padding:1.15rem 1.3rem}
.dbar{display:grid;grid-template-columns:96px 1fr 62px;gap:.7rem;align-items:center;margin:.55rem 0;font-size:.92rem;color:var(--txt)}
.dbar i{display:block;height:10px;border-radius:99px;background:linear-gradient(90deg,var(--violet),var(--teal))}
.dbar b{text-align:right;color:#fff;font-weight:600;font-variant-numeric:tabular-nums}
.peek{margin-top:.9rem;font-family:'Fira Code',monospace;font-size:.8rem;color:var(--muted);
  background:rgba(0,0,0,.28);border-radius:12px;padding:.65rem .85rem;overflow-x:auto;white-space:nowrap}
.cap{color:var(--muted);font-size:.82rem;margin-top:.6rem}
.mix{display:flex;height:14px;border-radius:99px;overflow:hidden;gap:2px;margin:.9rem 0 .7rem}
.mix i{display:block;height:100%}

@media (max-width:760px){
  .bento{grid-template-columns:1fr 1fr}
  .cell.main{grid-column:span 2;grid-row:auto}
  .cell.wide{grid-column:span 2}
  .strip{grid-template-columns:1fr 1fr}
  .strip>div:nth-child(3){border-left:0}
  .step .t small{display:none}
  .link{margin:0 .5rem}
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


# ============================================================
# Small helpers
# ============================================================

def H(markup):
    """Strip indentation and blank lines so Markdown never treats HTML as code."""
    return "\n".join(line.strip() for line in markup.splitlines() if line.strip())


def esc(value):
    return html.escape(str(value))


def md_inline(text):
    """Escape text, then keep **bold** and `code` from the AI's wording."""
    text = html.escape(str(text))
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


def human_size(num_bytes):
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:,.0f} {unit}" if unit == "B" else f"{size:,.1f} {unit}"
        size /= 1024


def tick(value):
    """Animated counting number (pure CSS)."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return esc(value)

    final = f"{number:,}"

    if number < 0 or number > 2_000_000_000:
        return f'<span class="tick"><span class="fin">{final}</span></span>'

    return (
        f'<span class="tick" style="--t:{number}">'
        f'<span class="cnt" aria-hidden="true"></span>'
        f'<span class="fin">{final}</span></span>'
    )


def format_number(value):
    """Format numeric values for cleaner display."""

    if isinstance(value, bool):
        return str(value)

    if isinstance(value, numbers.Integral):
        return f"{int(value):,}"

    if isinstance(value, numbers.Real):
        if pd.isna(value):
            return "N/A"

        return f"{float(value):,.2f}"

    return str(value)


PERCENT_HINT = re.compile(
    r"%|\b(percent|percentage|pct|share|rate|ratio|proportion|margin)\b",
    re.IGNORECASE,
)


def is_plain_number(value):
    return isinstance(value, numbers.Real) and not isinstance(value, bool)


APP_COLORWAY = ["#8B7CFF", "#3EE6C3", "#FF6FB5", "#FFC857", "#6FB8FF", "#B7A9FF"]

# Plotly Express paints each trace with its own default colour. These are
# those defaults, in order, so they can be swapped for the app's colours.
PX_DEFAULT_COLORS = [
    "#636efa", "#EF553B", "#00cc96", "#ab63fa", "#FFA15A",
    "#19d3f3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52",
]


def _app_color(color):
    """The app colour for a Plotly Express default colour, else unchanged."""
    if isinstance(color, str):
        text = color.lower()

        # Inside Streamlit, Plotly's default colours are placeholder codes
        # (#000001, #000002 ...) that the page swaps for real colours.
        if re.fullmatch(r"#0000[0-9a-f]{2}", text):
            position = int(text[1:], 16)
            if 1 <= position <= len(PX_DEFAULT_COLORS):
                return APP_COLORWAY[(position - 1) % len(APP_COLORWAY)]

        for index, default in enumerate(PX_DEFAULT_COLORS):
            if text == default.lower():
                return APP_COLORWAY[index % len(APP_COLORWAY)]

    return color


def style_figure(fig):
    """Match Plotly charts to the app's look (looks only, data untouched)."""
    try:
        fig = go.Figure(fig)
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            colorway=APP_COLORWAY,
            font=dict(family="Hanken Grotesk, sans-serif", color="#D7DBF5"),
        )

        for trace in fig.data:
            for part in ("marker", "line"):
                # not every trace type has both (a bar has no `line`)
                try:
                    holder = trace[part]
                    color = holder["color"]
                    if isinstance(color, str):
                        holder["color"] = _app_color(color)
                except (KeyError, ValueError, TypeError, AttributeError):
                    continue

        return fig
    except Exception:
        return fig


def show_dataframe(data, key=None, **kwargs):
    if key is not None:
        try:
            st.dataframe(data, key=key, **STRETCH, **kwargs)
            return
        except TypeError:
            pass

    st.dataframe(data, **STRETCH, **kwargs)


def show_figure(fig, key):
    # theme=None: Streamlit's own chart theme would repaint the colours
    st.plotly_chart(style_figure(fig), key=key, theme=None, **STRETCH)


# ============================================================
# Cached data steps (same functions, just not re-run on every click)
# ============================================================

class FileReadError(Exception):
    pass


class CleaningError(Exception):
    pass


def read_uploaded(file_bytes, file_name):
    """Read a CSV or Excel file into a DataFrame."""

    if not file_name.lower().endswith(".csv"):
        return pd.read_excel(io.BytesIO(file_bytes))

    # Excel often saves CSV files in a Windows encoding instead of UTF-8
    for encoding in ("utf-8", "latin-1"):
        try:
            frame = pd.read_csv(io.BytesIO(file_bytes), encoding=encoding)
            break
        except UnicodeDecodeError:
            continue

    # Some regional Excel settings save CSV files with ; between columns
    if frame.shape[1] == 1 and ";" in str(frame.columns[0]):
        frame = pd.read_csv(
            io.BytesIO(file_bytes), sep=";", encoding=encoding
        )

    return frame


def build_excel(df):
    exported = create_excel_export(df)

    if hasattr(exported, "getvalue"):
        return exported.getvalue()

    return exported


def prepare_data(signature, file_bytes, file_name):
    """
    Read and clean the file once per upload. The result lives in the
    session (not a shared cache), so nobody else's session can see it.
    """

    prepared = st.session_state.get("prepared")

    if prepared and prepared["signature"] == signature:
        return prepared

    try:
        raw_df = read_uploaded(file_bytes, file_name)
    except Exception as error:
        raise FileReadError(str(error)) from error

    try:
        cleaned_df, report = clean_data(raw_df)
    except Exception as error:
        raise CleaningError(str(error)) from error

    prepared = {
        "signature": signature,
        "df": cleaned_df,
        "report": report,
        "excel": None,
        "profile": None,
        "suggestions": None,
    }

    st.session_state["prepared"] = prepared

    return prepared


@st.cache_data(show_spinner=False)
def make_sample_csv():
    """A made-up sales file with the usual mess, for trying the app."""

    rng = np.random.default_rng(7)
    rows = 1200

    catalog = {
        "Laptop": ("Technology", 950, 0.18),
        "Monitor": ("Technology", 320, 0.20),
        "Headphones": ("Technology", 140, 0.28),
        "Keyboard": ("Technology", 70, 0.30),
        "Desk": ("Furniture", 480, 0.12),
        "Office Chair": ("Furniture", 260, 0.10),
        "Bookshelf": ("Furniture", 210, 0.08),
        "Notebooks": ("Office Supplies", 12, 0.40),
        "Pens": ("Office Supplies", 8, 0.45),
        "Printer Paper": ("Office Supplies", 25, 0.35),
        "Stapler": ("Office Supplies", 18, 0.38),
    }

    names = list(catalog)
    picks = rng.choice(names, rows)

    category = [catalog[p][0] for p in picks]
    price = np.array([catalog[p][1] for p in picks], dtype=float)
    margin = np.array([catalog[p][2] for p in picks], dtype=float)

    quantity = rng.integers(1, 9, rows)
    discount = rng.choice([0, 0, 0, 0.05, 0.1, 0.2], rows)

    sales = (price * quantity * (1 - discount)).round(2)
    profit = (
        sales * (margin - discount * 1.2 + rng.normal(0, 0.04, rows))
    ).round(2)

    days = rng.integers(0, 731, rows)
    dates = (
        pd.Timestamp("2024-01-01") + pd.to_timedelta(days, unit="D")
    ).strftime("%Y-%m-%d")

    frame = pd.DataFrame(
        {
            "Order ID": 10001 + np.arange(rows),
            "Order Date": dates,
            "Product": picks,
            "Category": category,
            "Region": rng.choice(
                ["Dubai", "Abu Dhabi", "Sharjah", "Ajman"],
                rows,
                p=[0.45, 0.28, 0.17, 0.10],
            ),
            "Quantity": quantity,
            "Sales": sales,
            "Profit": profit,
            "Discount": discount,
        }
    )

    frame = frame.sort_values("Order Date").reset_index(drop=True)

    # the usual mess: gaps, repeated rows and blank lines
    frame.loc[rng.choice(rows, 36, replace=False), "Discount"] = np.nan
    frame.loc[rng.choice(rows, 24, replace=False), "Region"] = np.nan

    repeats = frame.iloc[rng.choice(rows, 35, replace=False)]
    blanks = pd.DataFrame(
        [[np.nan] * frame.shape[1]] * 12, columns=frame.columns
    )

    frame = pd.concat([frame, repeats, blanks], ignore_index=True)
    frame = frame.sample(frac=1, random_state=11).reset_index(drop=True)

    return frame.to_csv(index=False).encode("utf-8")


# ============================================================
# Result display
# ============================================================

def display_result(result, question, key):
    """Display AI-generated analytical results cleanly."""

    # DataFrame
    if isinstance(result, pd.DataFrame):

        show_dataframe(result, hide_index=False, key=f"df_{key}")

    # Series
    elif isinstance(result, pd.Series):

        show_dataframe(result.to_frame(), key=f"sr_{key}")

    # Dictionary
    elif isinstance(result, dict):

        tiles = []

        for name, value in result.items():

            label = str(name).replace("_", " ").title()

            if is_plain_number(value):
                value_display = format_number(value)
            else:
                value_display = str(value)

            tiles.append(
                f'<div class="kv"><div class="lab">{esc(label)}</div>'
                f'<div class="num">{esc(value_display)}</div></div>'
            )

        st.markdown(
            H(f'<div class="kvgrid">{"".join(tiles)}</div>'),
            unsafe_allow_html=True,
        )

    # Plotly figure accidentally returned as result
    elif isinstance(result, go.Figure):

        st.warning(
            "The AI returned a chart as the result. "
            "The chart is displayed below."
        )

        show_figure(result, f"fig_as_result_{key}")

    # Numeric result
    elif is_plain_number(result):

        number = float(result)

        # Only call it a percentage when the question is about one
        if PERCENT_HINT.search(question) and 0 <= number <= 100:
            shown = f"{number:,.2f}%"
        else:
            shown = format_number(result)

        st.markdown(
            H(
                f'<div class="answer"><div class="lab">Answer</div>'
                f'<div class="num">{esc(shown)}</div></div>'
            ),
            unsafe_allow_html=True,
        )

    # Everything else
    else:

        text = str(result)
        size_class = "num text" if len(text) > 24 else "num"

        st.markdown(
            H(
                f'<div class="answer"><div class="lab">Answer</div>'
                f'<div class="{size_class}">{esc(text)}</div></div>'
            ),
            unsafe_allow_html=True,
        )


def with_follow_up_context(question, previous):
    """
    Turn a follow-up like "now only for 2025" into a full question by
    attaching the previous question and the code that answered it.
    """

    return (
        f"{question}\n\n"
        "This is a follow-up to an earlier question.\n"
        f"Earlier question: {previous['question']}\n"
        "Code that answered it:\n"
        f"{previous['analysis']['code']}\n\n"
        "Build on that analysis to answer the follow-up. "
        "Write complete code that sets `result` (and `fig` if useful)."
    )


def run_analysis(question, df, previous=None):
    """Ask the AI, run its code, retry with the error up to 3 times."""

    last_error = None
    analysis = None
    result = None
    fig = None
    attempts = 0

    question_for_ai = (
        with_follow_up_context(question, previous)
        if previous is not None
        else question
    )

    # Up to 3 attempts
    for attempt in range(3):

        attempts = attempt + 1

        try:

            analysis = generate_analysis_code(
                df,
                question_for_ai,
                previous_error=last_error,
            )

            result, fig = execute_analysis(
                analysis["code"],
                df,
            )

            last_error = None

            break

        except Exception as error:

            last_error = str(error)

    return {
        "question": question,
        "analysis": analysis,
        "result": result,
        "fig": fig,
        "error": last_error,
        "attempts": attempts,
        "follow_up": previous is not None,
    }


MAX_CSV_ROWS = 200_000


def index_is_meaningful(index):
    """False for the plain 0, 1, 2... row numbers pandas adds by itself."""

    if isinstance(index, pd.MultiIndex) or index.name is not None:
        return True

    return not pd.api.types.is_integer_dtype(index)


def result_to_csv(result):
    """CSV text for any kind of answer, or None if it is too big."""

    if isinstance(result, pd.DataFrame):

        if len(result) > MAX_CSV_ROWS:
            return None

        return result.to_csv(index=index_is_meaningful(result.index))

    if isinstance(result, pd.Series):

        if len(result) > MAX_CSV_ROWS:
            return None

        return result.to_frame().to_csv(
            index=index_is_meaningful(result.index)
        )

    if isinstance(result, dict):

        return pd.DataFrame(
            {
                "metric": [str(k) for k in result.keys()],
                "value": [str(v) for v in result.values()],
            }
        ).to_csv(index=False)

    if isinstance(result, go.Figure):
        return None

    return pd.DataFrame({"answer": [str(result)]}).to_csv(index=False)


def download(label, data, file_name, mime, key, primary=False):
    """Download button that does not rerun the page on newer Streamlit."""

    kwargs = dict(
        label=label,
        data=data,
        file_name=file_name,
        mime=mime,
        key=key,
    )

    if primary:
        kwargs["type"] = "primary"

    if _version_tuple() >= (1, 45):
        kwargs["on_click"] = "ignore"

    try:
        st.download_button(**kwargs)
    except TypeError:
        kwargs.pop("type", None)
        kwargs.pop("on_click", None)
        st.download_button(**kwargs)


def render_downloads(entry, turn_id):
    """Save the answer: result as CSV, chart as an interactive page."""

    csv_text = result_to_csv(entry["result"])

    chart_html = None

    if entry["fig"] is not None:
        try:
            # the original chart (not the dark-styled copy) so it also
            # looks right on a white page
            chart_html = entry["fig"].to_html(include_plotlyjs="cdn")
        except Exception:
            chart_html = None

    if csv_text is None and chart_html is None:
        return

    columns = st.columns([1, 1, 2])

    if csv_text is not None:
        with columns[0]:
            download(
                "⬇ Result (CSV)",
                csv_text,
                f"result_{turn_id + 1}.csv",
                "text/csv",
                f"dl_csv_{turn_id}",
            )

    if chart_html is not None:
        with columns[1]:
            download(
                "⬇ Chart (HTML)",
                chart_html,
                f"chart_{turn_id + 1}.html",
                "text/html",
                f"dl_chart_{turn_id}",
            )


def render_turn(entry, turn_id, columns):
    """One question and its answer, laid out like a chat."""

    with st.chat_message("user", avatar="🙂"):

        if entry.get("follow_up"):
            st.markdown(
                '<span class="tag soft">Follow-up</span>',
                unsafe_allow_html=True,
            )

        st.markdown(entry["question"])

    with st.chat_message("assistant", avatar="✨"):

        analysis = entry["analysis"] or {}

        # ----- failed after retries -----
        if entry["error"] is not None:

            sample = ", ".join(str(c).replace("_", " ") for c in list(columns)[:6])

            st.markdown(
                H(
                    f"""<div class="errbox"><b>The AI couldn't answer that after {entry['attempts']} tries.</b><br>
                    Try rephrasing with the exact thing to calculate, for example
                    “total profit by product”. Columns in your data: {esc(sample)}.</div>"""
                ),
                unsafe_allow_html=True,
            )

            with st.expander("Technical error"):
                st.code(entry["error"], language="text")

            if analysis.get("code"):
                with st.expander("Last code the AI tried"):
                    st.code(analysis["code"], language="python")

            return

        # ----- success -----
        if entry["attempts"] > 1:
            st.markdown(
                f'<span class="tag">Fixed itself on attempt {entry["attempts"]}</span>',
                unsafe_allow_html=True,
            )

        explanation = analysis.get("explanation")

        if explanation:
            st.markdown(explanation)

        st.markdown('<div class="lab">Result</div>', unsafe_allow_html=True)

        display_result(entry["result"], entry["question"], turn_id)

        if entry["fig"] is not None:

            st.markdown('<div class="lab">Visualization</div>', unsafe_allow_html=True)

            show_figure(entry["fig"], f"fig_{turn_id}")

        render_downloads(entry, turn_id)

        if analysis.get("code"):
            with st.expander("View Generated Python Code"):

                st.code(
                    analysis["code"],
                    language="python",
                )


# ============================================================
# Suggestions and callbacks
# ============================================================

def suggest_questions(df):
    """Example questions built from the dataset's own columns."""

    def nice(name):
        return str(name).replace("_", " ")

    def plural(word):
        word = nice(word)

        if word.endswith("s"):
            return word

        if word.endswith("y") and word[-2:-1] not in ("a", "e", "i", "o", "u"):
            return word[:-1] + "ies"

        return word + "s"

    money_words = ("sales", "revenue", "profit", "amount", "total", "price", "cost")

    def money_first(name):
        text = str(name).lower()
        return 0 if any(w in text for w in money_words) else 1

    def unique_count(series):
        try:
            return series.nunique()
        except Exception:
            return 10**9

    def looks_like_id(name):
        text = str(name).lower()
        return (
            text in ("id", "index")
            or text.endswith("_id")
            or text.endswith(" id")
            or text.startswith("id_")
            or text.endswith("_index")
        )

    numeric = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c])
        and not pd.api.types.is_bool_dtype(df[c])
        and not looks_like_id(c)
    ]

    id_numeric = [
        c for c in df.columns
        if pd.api.types.is_numeric_dtype(df[c]) and looks_like_id(c)
    ]

    # sales / profit style columns first, counts like quantity after
    numeric.sort(key=money_first)

    dates = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]

    categories = [
        c for c in df.columns
        if c not in numeric
        and c not in id_numeric
        and c not in dates
        and 1 < unique_count(df[c]) <= 50
    ]

    ideas = []

    if categories and numeric:
        ideas.append(f"What are the top 10 {plural(categories[0])} by total {nice(numeric[0])}?")

    if categories and numeric:
        ideas.append(
            f"Which {nice(categories[-1])} has the highest average {nice(numeric[-1])}?"
        )

    if numeric:
        ideas.append(f"What is the average {nice(numeric[0])}?")

    if dates and numeric:
        ideas.append(f"How does total {nice(numeric[0])} change over time?")

    if categories:
        ideas.append(f"How many rows are there for each {nice(categories[0])}?")

    ideas.append("Which columns have the most missing values?")

    unique_ideas = []

    for idea in ideas:
        if idea not in unique_ideas:
            unique_ideas.append(idea)

    return unique_ideas[:5]


def pick_question(question):
    st.session_state["q_input"] = question
    st.session_state["run_now"] = True


def use_sample_data():
    st.session_state["use_sample"] = True


def use_own_file():
    st.session_state["use_sample"] = False


def download_cleaned(prepared, key):
    """Excel download. Big files are only built after a click."""

    if prepared["excel"] is None:

        if len(prepared["df"]) > EAGER_EXCEL_ROWS:

            if not st.button(
                "Prepare Excel file",
                key=f"prep_{key}",
                help=(
                    "Large file: building the Excel file takes a moment, "
                    "so it only happens when you ask."
                ),
            ):
                return

        try:
            with st.spinner("Building the Excel file..."):
                prepared["excel"] = build_excel(prepared["df"])
        except Exception as error:
            st.warning(f"Could not build the Excel export: {error}")
            return

    download(
        "⬇️ Download Cleaned Excel File",
        prepared["excel"],
        "cleaned_data.xlsx",
        (
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        key,
        primary=True,
    )


# ============================================================
# Stepper
# ============================================================

def stepper_html(loaded, summary_done, asked):
    states = [
        ("Upload", "your file", loaded),
        ("Clean", "automatic", loaded),
        ("Summarize", "optional", summary_done),
        ("Ask", "plain English", asked),
    ]

    current = next((i for i, s in enumerate(states) if not s[2]), len(states))
    last_done = max((i for i, s in enumerate(states) if s[2]), default=-1)
    parts = []

    for i, (label, hint, done) in enumerate(states):

        if done:
            css, mark = "done", "✓"
        elif i == current and i > last_done:
            css, mark = "now", str(i + 1)
        else:
            css, mark = "", str(i + 1)

        parts.append(
            f'<div class="step {css}"><span class="dot">{mark}</span>'
            f'<span class="t"><b>{label}</b><small>{hint}</small></span></div>'
        )

        if i < len(states) - 1:
            link_css = "done" if done else ""
            parts.append(f'<div class="link {link_css}"></div>')

    return H(f'<div class="steps">{"".join(parts)}</div>')


# ============================================================
# Session state
# ============================================================

st.session_state.setdefault("file_sig", None)
st.session_state.setdefault("history", [])
st.session_state.setdefault("summary", None)
st.session_state.setdefault("run_now", False)
st.session_state.setdefault("q_input", "")
st.session_state.setdefault("use_sample", False)
st.session_state.setdefault("prepared", None)


# ============================================================
# Header + upload
# ============================================================

left, right = st.columns([1.12, 1], gap="large")

with left:

    hero_placeholder = st.empty()

    uploaded_file = st.file_uploader(
        "Upload your dataset",
        type=["csv", "xlsx", "xls"],
        key="uploader",
        label_visibility="collapsed",
    )

    sample_slot = st.empty()

with right:

    side_placeholder = st.empty()

steps_placeholder = st.empty()


# A real upload always wins over the sample file
if uploaded_file is not None:
    st.session_state["use_sample"] = False

using_sample = uploaded_file is None and st.session_state["use_sample"]


# ============================================================
# Nothing uploaded yet: invite the first action
# ============================================================

if uploaded_file is None and not using_sample:

    st.session_state["file_sig"] = None
    st.session_state["history"] = []
    st.session_state["summary"] = None
    st.session_state["prepared"] = None

    hero_placeholder.markdown(
        H(
            """<div class="hero-title">Ask your spreadsheet anything.</div>
            <p class="hero-sub">Upload a CSV or Excel file. It gets cleaned automatically,
            then you ask questions in plain English and get tables, charts and the Python behind them.</p>"""
        ),
        unsafe_allow_html=True,
    )

    with sample_slot.container():

        st.button(
            "Try it with sample data",
            key="try_sample",
            on_click=use_sample_data,
        )

        st.markdown(
            '<p class="samplehint">No file handy? Explore a made-up sales '
            "file with duplicates, gaps and blank rows.</p>",
            unsafe_allow_html=True,
        )

    side_placeholder.markdown(
        H(
            """<div class="demo">
            <div class="bq">Which three products earn the most profit?</div>
            <div class="ba">
              <div class="lab">Example answer</div>
              <div class="dbar"><span>Product A</span><i style="width:100%"></i><b>48.2k</b></div>
              <div class="dbar"><span>Product B</span><i style="width:72%"></i><b>34.8k</b></div>
              <div class="dbar"><span>Product C</span><i style="width:51%"></i><b>24.6k</b></div>
              <div class="peek">df.groupby("product")["profit"].sum().nlargest(3)</div>
            </div>
            <div class="cap">Example only. Your own data will show up here.</div>
            </div>"""
        ),
        unsafe_allow_html=True,
    )

    steps_placeholder.markdown(
        stepper_html(False, False, False),
        unsafe_allow_html=True,
    )

    with st.sidebar:

        st.markdown(
            H(
                """<div class="brand"><span class="orb"></span>AI Data Analysis</div>
                <div class="howto"><b>How it works</b><br>
                Drop a file in the upload box.<br>
                We remove empty rows, duplicates and messy column names.<br>
                Ask a question and the AI writes and runs the analysis for you.</div>"""
            ),
            unsafe_allow_html=True,
        )

    st.stop()


# ============================================================
# Read file
# ============================================================

if using_sample:
    source_name = SAMPLE_NAME
    file_bytes = make_sample_csv()
else:
    source_name = uploaded_file.name
    file_bytes = uploaded_file.getvalue()

signature = (
    f"{source_name}:{len(file_bytes)}:"
    f"{hashlib.md5(file_bytes).hexdigest()[:12]}"
)

if st.session_state["file_sig"] != signature:
    st.session_state["file_sig"] = signature
    st.session_state["history"] = []
    st.session_state["summary"] = None
    st.session_state["run_now"] = False
    st.session_state["q_input"] = ""


# ============================================================
# Clean data (read once per file, then kept in the session)
# ============================================================

try:

    prepared = prepare_data(signature, file_bytes, source_name)

except FileReadError as error:

    st.error(
        f"Could not read the uploaded file: {error}"
    )

    st.stop()

except CleaningError as error:

    st.error(f"Could not clean this dataset: {error}")

    st.stop()

cleaned_df = prepared["df"]
report = prepared["report"]


def r(key):
    """Read a number from the cleaning report."""
    try:
        return int(report.get(key, 0))
    except (TypeError, ValueError):
        return 0


# ============================================================
# Hero (file loaded) + sidebar
# ============================================================

if using_sample:

    hero_placeholder.markdown(
        H(
            """<div class="hero-title compact">Exploring the sample data.</div>
            <p class="hero-sub">This is a made-up sales file, cleaned just like
            yours would be. Try the tabs, or ask it a question.</p>"""
        ),
        unsafe_allow_html=True,
    )

else:

    hero_placeholder.markdown(
        H(
            """<div class="hero-title compact">Your data is clean and ready.</div>
            <p class="hero-sub">Look around the tabs below, or jump to
            <b>Ask Your Data</b> and type a question.</p>"""
        ),
        unsafe_allow_html=True,
    )


def safe_unique(series):
    try:
        return int(series.nunique())
    except Exception:
        return 0


def column_mix(frame):
    counts = {"Numbers": 0, "Text": 0, "Dates": 0, "Other": 0}

    for column in frame.columns:
        series = frame[column]

        if pd.api.types.is_bool_dtype(series):
            counts["Other"] += 1
        elif pd.api.types.is_numeric_dtype(series):
            counts["Numbers"] += 1
        elif pd.api.types.is_datetime64_any_dtype(series):
            counts["Dates"] += 1
        elif (
            pd.api.types.is_string_dtype(series)
            or pd.api.types.is_object_dtype(series)
            or isinstance(series.dtype, pd.CategoricalDtype)
        ):
            counts["Text"] += 1
        else:
            counts["Other"] += 1

    return counts


mix_counts = column_mix(cleaned_df)
mix_colors = {
    "Numbers": "var(--violet)",
    "Text": "var(--teal)",
    "Dates": "var(--pink)",
    "Other": "#7B86B8",
}
total_columns = max(sum(mix_counts.values()), 1)

mix_bar = "".join(
    f'<i style="width:{count / total_columns * 100:.2f}%;background:{mix_colors[name]}"></i>'
    for name, count in mix_counts.items()
    if count
)

mix_legend = "".join(
    f'<span><b style="background:{mix_colors[name]}"></b>{name} <strong>{count}</strong></span>'
    for name, count in mix_counts.items()
    if count
)

side_placeholder.markdown(
    H(
        f"""<div class="glass">
        <div class="lab">{esc(source_name)}</div>
        <div class="num">{tick(len(cleaned_df.columns))} <span style="font-size:1.1rem;font-weight:500;color:var(--muted)">columns</span></div>
        <div class="mix">{mix_bar}</div>
        <div class="legend">{mix_legend}</div>
        </div>"""
    ),
    unsafe_allow_html=True,
)

with st.sidebar:

    st.markdown(
        H(
            f"""<div class="brand"><span class="orb"></span>AI Data Analysis</div>
            <div class="fcard">
              <div class="fname">{esc(source_name)}</div>
              <div class="fmeta">{len(cleaned_df):,} rows, {len(cleaned_df.columns):,} columns</div>
              <div class="fmeta">{human_size(len(file_bytes))}</div>
            </div>"""
        ),
        unsafe_allow_html=True,
    )

    download_cleaned(prepared, "dl_sidebar")

    if using_sample:

        st.markdown(
            '<p class="samplehint" style="margin-top:1rem">Sample data is on. '
            "Upload your own file any time.</p>",
            unsafe_allow_html=True,
        )

        st.button(
            "Use my own file",
            key="use_own",
            on_click=use_own_file,
        )


# ============================================================
# Tabs
# ============================================================

tab_overview, tab_cleaning, tab_summary, tab_ask = st.tabs(
    ["Overview", "Cleaning", "Summary", "Ask Your Data"]
)


# ------------------------------------------------------------
# Overview
# ------------------------------------------------------------

with tab_overview:

    original_rows = r("original_rows")
    final_rows = r("final_rows")
    kept_pct = (final_rows / original_rows * 100) if original_rows else 100.0
    duplicate_count = r("duplicates_removed")
    dup_pct = (duplicate_count / original_rows * 100) if original_rows else 0.0

    dup_note = (
        "No duplicate rows found."
        if duplicate_count == 0
        else f"{dup_pct:.1f}% of the original rows were duplicates."
    )

    if len(cleaned_df) >= LARGE_ROWS:

        st.markdown(
            H(
                f"""<div class="notebox"><b>Large file: {len(cleaned_df):,} rows.</b>
                Tables show the first rows only. Questions can take longer to answer,
                and the Excel file is built when you ask for it.</div>"""
            ),
            unsafe_allow_html=True,
        )

    st.markdown(
        H(
            f"""<div class="bento">
            <div class="cell main">
              <div>
                <div class="lab">Final rows</div>
                <div class="num xl">{tick(final_rows)}</div>
              </div>
              <div>
                <div class="meter"><i style="width:{min(kept_pct, 100):.1f}%"></i></div>
                <div class="sub">{kept_pct:.1f}% of your {original_rows:,} original rows made it through cleaning.</div>
              </div>
            </div>
            <div class="cell"><div class="lab">Original rows</div><div class="num">{tick(original_rows)}</div></div>
            <div class="cell"><div class="lab">Columns</div><div class="num">{tick(r("final_columns"))}</div></div>
            <div class="cell wide"><div class="lab">Duplicates removed</div><div class="num">{tick(duplicate_count)}</div><div class="sub">{dup_note}</div></div>
            </div>"""
        ),
        unsafe_allow_html=True,
    )

    st.markdown("### Columns at a glance")

    try:
        if prepared["profile"] is None:
            prepared["profile"] = pd.DataFrame(
                {
                    "column": [str(c) for c in cleaned_df.columns],
                    "type": [str(t) for t in cleaned_df.dtypes],
                    "filled (%)": [
                        float((1 - cleaned_df[c].isna().mean()) * 100)
                        for c in cleaned_df.columns
                    ],
                    "unique values": [
                        safe_unique(cleaned_df[c])
                        for c in cleaned_df.columns
                    ],
                }
            )

        show_dataframe(
            prepared["profile"],
            hide_index=True,
            column_config={
                "filled (%)": st.column_config.ProgressColumn(
                    "filled (%)",
                    min_value=0,
                    max_value=100,
                    format="%.0f%%",
                )
            },
        )
    except Exception:
        pass

    st.markdown("### Cleaned data preview")

    show_dataframe(cleaned_df.head(10))


# ------------------------------------------------------------
# Cleaning
# ------------------------------------------------------------

with tab_cleaning:

    total = original_rows if original_rows else (r("final_rows") + r("rows_removed"))
    total = max(total, 1)

    empty_rows = r("empty_rows_removed")
    dups = r("duplicates_removed")
    other_removed = max(r("rows_removed") - empty_rows - dups, 0)

    def seg(css, count):
        if count <= 0:
            return ""
        width = max(count / total * 100, 1.2)
        return f'<i class="{css}" style="width:{width:.2f}%"></i>'

    legend_items = [
        f'<span><b style="background:var(--teal)"></b>Kept <strong>{r("final_rows"):,}</strong></span>'
    ]

    for css_color, name, count in (
        ("var(--pink)", "Duplicates", dups),
        ("var(--amber)", "Empty rows", empty_rows),
        ("#7B86B8", "Other", other_removed),
    ):
        if count:
            legend_items.append(
                f'<span><b style="background:{css_color}"></b>{name} <strong>{count:,}</strong></span>'
            )

    st.markdown(
        H(
            f"""<div class="glass">
            <div class="lab">What happened to your {total:,} rows</div>
            <div class="flowbar">{seg("k", r("final_rows"))}{seg("d", dups)}{seg("e", empty_rows)}{seg("o", other_removed)}</div>
            <div class="legend">{"".join(legend_items)}</div>
            </div>
            <div class="strip">
              <div><div class="lab">Rows removed</div><div class="num">{tick(r("rows_removed"))}</div></div>
              <div><div class="lab">Empty rows</div><div class="num">{tick(empty_rows)}</div></div>
              <div><div class="lab">Missing values found</div><div class="num">{tick(r("missing_values_found"))}</div></div>
              <div><div class="lab">Missing values remaining</div><div class="num">{tick(r("missing_values_remaining"))}</div></div>
            </div>"""
        ),
        unsafe_allow_html=True,
    )

    st.markdown("### View Cleaning Actions")

    def tl(text, count=None, warn=False):
        css = "tl"
        if count is not None and count == 0:
            css += " idle"
        if warn:
            css += " warn"
        return f'<div class="{css}">{text}</div>'

    remaining = r("missing_values_remaining")

    found = r("missing_values_found")

    date_names = [
        str(c) for c in (report.get("date_columns") or [])
    ]

    steps = (
        tl(f'Removed <strong>{empty_rows:,}</strong> completely empty rows', empty_rows)
        + tl(f'Removed <strong>{dups:,}</strong> duplicate rows', dups)
        + tl(
            f'Removed <strong>{r("empty_columns_removed"):,}</strong> completely empty columns',
            r("empty_columns_removed"),
        )
        + tl(
            f'Detected <strong>{found:,}</strong> missing values',
            found,
        )
    )

    if found:
        steps += tl(
            "Filled missing numbers with the column median "
            "and missing text with “Unknown”"
        )

    if date_names:
        shown = ", ".join(f"<code>{esc(c)}</code>" for c in date_names[:6])
        steps += tl(f"Converted {shown} to real dates")

    steps += tl(
        f'Remaining missing values: <strong>{remaining:,}</strong>',
        None,
        warn=remaining > 0,
    )

    steps += tl("Standardized column names")

    st.markdown(
        H(f'<div class="timeline">{steps}</div>'),
        unsafe_allow_html=True,
    )

    st.markdown("### Export")

    download_cleaned(prepared, "dl_cleaning")


# ------------------------------------------------------------
# Executive Summary
# ------------------------------------------------------------

with tab_summary:

    st.markdown("### Executive Summary")

    st.markdown(
        '<p class="hero-sub" style="margin-bottom:1rem">'
        "Key findings and one recommendation, with every number calculated "
        "straight from your cleaned data.</p>",
        unsafe_allow_html=True,
    )

    if st.button(
        "Generate Executive Summary",
        type="primary",
        key="gen_summary",
    ):

        with st.spinner(
            "Generating executive summary..."
        ):

            try:

                st.session_state["summary"] = generate_executive_summary(
                    cleaned_df
                )

            except Exception as error:

                st.session_state["summary"] = None

                st.error(
                    "The summary could not be calculated for this dataset."
                )

                with st.expander("Technical Error"):
                    st.code(str(error), language="text")

    summary = st.session_state["summary"]

    if summary:

        st.markdown("### Key Insights")

        for insight in summary["insights"]:

            st.markdown(
                f'<div class="insight">{md_inline(insight)}</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            H(
                f"""<div class="reco"><h4>Recommendation</h4>
                <p>{md_inline(summary["recommendation"])}</p></div>"""
            ),
            unsafe_allow_html=True,
        )


# ------------------------------------------------------------
# Ask Your Data
# ------------------------------------------------------------

with tab_ask:

    st.markdown("### Ask Your Data")

    st.markdown(
        '<p class="hero-sub" style="margin-bottom:.9rem">'
        "Ask a business question about your dataset using natural language. "
        "Pick a suggestion or type your own.</p>",
        unsafe_allow_html=True,
    )

    history = st.session_state["history"]

    submitted = False
    question = ""

    if AI_SETUP_ERROR is not None:

        st.session_state["run_now"] = False

        if "GROQ_API_KEY" in AI_SETUP_ERROR:
            setup_hint = (
                "Add your key as <code>GROQ_API_KEY</code> in a <code>.env</code> "
                "file (see <code>.env.example</code>) or in Streamlit secrets, "
                "then restart the app.<br>"
            )
        else:
            setup_hint = (
                f"{esc(AI_SETUP_ERROR)}<br>"
                "Install the requirements with "
                "<code>pip install -r requirements.txt</code> and restart the app.<br>"
            )

        st.markdown(
            H(
                f"""<div class="notebox"><b>Questions are switched off: the AI is not set up.</b><br>
                {setup_hint}
                Cleaning, the summary and the Excel download work without it.</div>"""
            ),
            unsafe_allow_html=True,
        )

    else:

        if prepared["suggestions"] is None:
            prepared["suggestions"] = suggest_questions(cleaned_df)

        with keyed_container("chips"):

            for index, idea in enumerate(prepared["suggestions"]):

                st.button(
                    idea,
                    key=f"chip_{index}",
                    on_click=pick_question,
                    args=(idea,),
                )

        # the latest answer that worked, if any, can be built on
        previous = next(
            (
                e for e in reversed(history)
                if e["error"] is None and e["analysis"]
            ),
            None,
        )

        follow_up = False

        if previous is not None:

            follow_up = st.toggle(
                "Follow up on my last answer",
                key="follow_up",
                help=(
                    "Turn on to build on the previous answer, "
                    "for example “now only for Dubai”."
                ),
            )

        with keyed_container("askwrap"):

            with st.form("ask_form", border=False) if _version_tuple() >= (1, 41) else st.form("ask_form"):

                input_col, button_col = st.columns([6, 1.2])

                question = input_col.text_input(
                    "Ask a question about your dataset",
                    placeholder=(
                        "Example: What are the top 10 products by profit?"
                    ),
                    key="q_input",
                    label_visibility="collapsed",
                )

                submitted = button_col.form_submit_button(
                    "Analyze",
                    type="primary",
                )

    run_now = st.session_state.pop("run_now", False)

    if AI_SETUP_ERROR is None and (submitted or run_now):

        if not question.strip():

            st.warning(
                "Please enter a question."
            )

        else:

            with st.spinner(
                "AI is analyzing your data..."
            ):

                entry = run_analysis(
                    question.strip(),
                    cleaned_df,
                    previous if follow_up else None,
                )

            st.session_state["history"].append(entry)

            # draw the page again so the follow-up switch and the
            # answer both reflect the new history
            st.rerun()

    history = st.session_state["history"]

    if not history:

        st.markdown(
            '<div class="empty">Your questions and answers will show up here.</div>',
            unsafe_allow_html=True,
        )

    else:

        newest_first = list(enumerate(history))[::-1]

        first_index, first_entry = newest_first[0]

        render_turn(first_entry, first_index, cleaned_df.columns)

        if len(newest_first) > 1:

            st.markdown("### Earlier questions")

            for turn_index, entry in newest_first[1:]:

                title = entry["question"]

                if len(title) > 90:
                    title = title[:87] + "..."

                with st.expander(title):
                    render_turn(entry, turn_index, cleaned_df.columns)


# ============================================================
# Stepper (filled last so it reflects what just happened)
# ============================================================

steps_placeholder.markdown(
    stepper_html(
        True,
        bool(st.session_state["summary"]),
        bool(st.session_state["history"]),
    ),
    unsafe_allow_html=True,
)
