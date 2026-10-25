"""Shared visual theme: palette, CSS and small HTML helpers.

Palette: warm stone background, deep teal (primary) and copper (accent).
"""

import base64
import html
from datetime import datetime
from pathlib import Path

import streamlit as st

# ---- palette ---------------------------------------------------------------
BG = "#F2F0EA"
SURFACE = "#FFFFFF"
LINE = "#E3DFD5"
INK = "#1B2220"
MUTED = "#6C746F"
TEAL = "#0F5B57"
DEEP = "#0B3B38"
COPPER = "#C8622B"
OK = "#3C9A6B"
WARN = "#E3A02F"
CRIT = "#D2453A"

CONDITION_COLOURS = {"NORMAL": OK, "WARNING": WARN, "CRITICAL": CRIT}
RISK_COLOURS = {"Low": OK, "Medium": WARN, "High": "#E07B2C", "Critical": CRIT}

esc = html.escape

_VARS = (f":root {{ --bg:{BG}; --surface:{SURFACE}; --line:{LINE}; --ink:{INK}; --muted:{MUTED}; "
         f"--teal:{TEAL}; --deep:{DEEP}; --copper:{COPPER}; --ok:{OK}; --warn:{WARN}; --crit:{CRIT}; }}")

_CSS = r"""
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
.stApp { background: var(--bg); }
.block-container { padding-top: 2.4rem; padding-bottom: 2.5rem; max-width: 1500px; }

/* ---------- App header (logged-in) ---------- */
.st-key-appheader { background: var(--deep); border-radius: 14px; padding: .65rem 1.1rem; }
.st-key-appheader * { color: #E8F0EE; }
.st-key-appheader button { background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.28); border-radius: 8px; width: 100%; }
.st-key-appheader button:hover { background: var(--copper); border-color: var(--copper); }
.st-key-appheader button p { color: #fff; font-size: .85rem; margin: 0; }
.brand-row { display: flex; align-items: center; gap: .7rem; }
.brand-row .name { font-weight: 800; letter-spacing: .06em; line-height: 1.1; color: #fff; }
.brand-row .sub { font-size: .66rem; text-transform: uppercase; letter-spacing: .16em; opacity: .7; }
.user-chip { text-align: right; font-size: .8rem; line-height: 1.3; }
.user-chip b { color: #fff; }
.stamp { font-size: .8rem; opacity: .85; white-space: nowrap; }
.live-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #5BD39B; margin-right: .5rem;
    box-shadow: 0 0 0 0 rgba(91,211,155,.7); animation: pulse 2s infinite; }
@keyframes pulse { 70% { box-shadow: 0 0 0 7px rgba(91,211,155,0); } 100% { box-shadow: 0 0 0 0 rgba(91,211,155,0); } }

/* ---------- Top navigation tabs ---------- */
.st-key-topnav { background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: .1rem .4rem; margin: .7rem 0 1.3rem; }
.st-key-topnav button { width: 100%; background: transparent; border: none; border-bottom: 3px solid transparent; border-radius: 0;
    box-shadow: none; padding: .6rem .3rem; color: var(--muted); }
.st-key-topnav button p { color: inherit; font-size: .88rem; font-weight: 600; margin: 0; }
.st-key-topnav button:hover { background: rgba(15,91,87,.07); color: var(--teal); }
.st-key-topnav button[kind="primary"], .st-key-topnav button[data-testid="stBaseButton-primary"] {
    background: transparent; color: var(--teal); border-bottom: 3px solid var(--copper); }
.st-key-topnav button[kind="primary"] p, .st-key-topnav button[data-testid="stBaseButton-primary"] p { font-weight: 800; }

/* ---------- Page header / labels ---------- */
.page-head { border-bottom: 1px solid var(--line); padding-bottom: .55rem; margin-bottom: .9rem; }
.page-head h1 { font-size: 1.65rem; margin: 0; color: var(--ink); font-weight: 800; letter-spacing: -.01em; }
.page-head p { margin: .15rem 0 0; color: var(--muted); font-size: .9rem; }
.section-label { font-size: .74rem; font-weight: 800; color: var(--teal); text-transform: uppercase; letter-spacing: .14em; margin: 1.5rem 0 .6rem; }

/* ---------- Panels, chips ---------- */
.panel { background: #fff; border: 1px solid var(--line); border-radius: 14px; padding: 1rem 1.2rem; margin-bottom: 1rem; }
.panel-title { font-size: .74rem; font-weight: 800; color: var(--teal); text-transform: uppercase; letter-spacing: .13em; margin-bottom: .6rem; }
.chips { margin: .2rem 0 1.1rem; }
.chip { display: inline-flex; align-items: center; gap: .45rem; padding: .34rem .85rem; border-radius: 999px; font-size: .82rem;
    font-weight: 600; border: 1px solid; margin: 0 .5rem .5rem 0; }
.chip::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
.chip.crit { background: #FBE9E7; color: #9E2B22; border-color: #F2C4BF; }
.chip.warn { background: #FCF3E0; color: #8A5A07; border-color: #F0D9A6; }
.chip.ok { background: #EAF5EF; color: #25704A; border-color: #BFE0CE; }
.chip.info { background: #E6F1F0; color: var(--teal); border-color: #BCD9D6; }

/* ---------- Ledger strip ---------- */
.ledger { padding: 0; overflow: hidden; }
.lrow { display: flex; align-items: stretch; }
.lrow + .lrow { border-top: 1px solid var(--line); }
.lname { flex: 0 0 96px; width: 96px; padding: .9rem 1rem; background: #F7F5F0; font-size: .72rem; font-weight: 800; letter-spacing: .13em;
    text-transform: uppercase; color: var(--teal); display: flex; flex-direction: column; justify-content: center; }
.lname small { font-weight: 600; letter-spacing: .04em; text-transform: none; color: var(--muted); margin-top: .15rem; }
.lstat { flex: 1 1 0; min-width: 0; padding: .8rem .9rem; border-left: 1px solid var(--line); }
.lstat b { display: block; font-size: 1.5rem; line-height: 1.15; color: var(--ink); letter-spacing: -.02em; }
.lstat span { font-size: .66rem; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; font-weight: 600; }
.lstat.crit b { color: var(--crit); } .lstat.warn b { color: #B97A12; } .lstat.ok b { color: var(--ok); }

/* ---------- Equipment status board ---------- */
.board { display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: .55rem; }
.tile { position: relative; background: var(--t); border: 1px solid var(--line); border-top: 4px solid var(--c); border-radius: 10px; padding: .5rem .65rem .55rem; }
.tile b { display: block; font-size: .86rem; color: var(--ink); }
.tile span { display: block; font-size: .7rem; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tile .row { display: flex; align-items: center; justify-content: space-between; gap: .3rem; margin-top: .15rem; }
.tile i { font-style: normal; font-size: 1.15rem; font-weight: 800; color: var(--ink); }
.tile em { font-style: normal; font-size: .58rem; font-weight: 800; text-transform: uppercase;
    letter-spacing: .06em; background: var(--ink); color: #fff; border-radius: 4px; padding: .08rem .3rem; }
.legend { display: flex; flex-wrap: wrap; gap: 1rem; margin-top: .8rem; font-size: .76rem; color: var(--muted); }
.lg i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: .4rem; vertical-align: -1px; }

/* ---------- Action list / risk bar ---------- */
.item { display: flex; gap: .7rem; padding: .6rem 0; border-top: 1px solid var(--line); }
.item:first-of-type { border-top: none; padding-top: .1rem; }
.item b { display: block; font-size: .88rem; color: var(--ink); }
.item small { display: block; color: var(--muted); font-size: .76rem; }
.dot { flex: 0 0 10px; height: 10px; margin-top: .35rem; border-radius: 50%; background: var(--muted); }
.dot.crit { background: var(--crit); } .dot.warn { background: var(--warn); } .dot.ok { background: var(--ok); } .dot.info { background: var(--teal); }
.segbar { display: flex; height: 14px; border-radius: 7px; overflow: hidden; gap: 2px; }
.seg { min-width: 4px; }

/* ---------- Charts ---------- */
div[data-testid="stPlotlyChart"] { background: #fff; border: 1px solid var(--line); border-radius: 14px; padding: .4rem; }

/* ---------- Login ---------- */
.login-brand { position: relative; overflow: hidden; background: linear-gradient(165deg, var(--deep) 0%, #0F4A47 100%);
    color: #fff; border-radius: 16px; padding: 3rem 2.4rem 3.4rem; min-height: 540px; }
.login-brand::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 12px;
    background: repeating-linear-gradient(135deg, var(--copper) 0 14px, #1B2220 14px 28px); }
.login-brand h1 { color: #fff; font-size: 2.1rem; line-height: 1.15; margin: 1.1rem 0 .9rem; letter-spacing: -.01em; }
.login-brand p { color: #C5D8D5; font-size: .95rem; }
.login-brand ul { list-style: none; padding: 0; margin: 1.6rem 0 0; }
.login-brand li { padding: .38rem 0; color: #E8F0EE; font-size: .92rem; }
.login-brand li::before { content: "▸"; color: #F0A56B; margin-right: .6rem; }
.login-credit { position: absolute; left: 2.4rem; right: 2.4rem; bottom: 1.5rem; font-size: .68rem; letter-spacing: .04em;
    color: #E8F0EE; text-shadow: 0 1px 3px rgba(0,0,0,.65); }
.login-tag { font-size: .72rem; letter-spacing: .18em; text-transform: uppercase; color: #F0A56B; font-weight: 800; }
.login-head h2 { color: var(--ink); margin-bottom: .1rem; }
.login-head p { color: var(--muted); font-size: .9rem; margin-bottom: 1rem; }
div[data-testid="stForm"] { background: #fff; border: 1px solid var(--line); border-radius: 14px; padding: 1.4rem; }
div[data-testid="stForm"] button { width: 100%; background: var(--teal); color: #fff; border: none; }
div[data-testid="stForm"] button:hover { background: var(--copper); color: #fff; }
"""


def apply_theme() -> None:
    st.markdown(f"<style>{_VARS}{_CSS}</style>", unsafe_allow_html=True)


# ---- small HTML helpers ----------------------------------------------------
def page_header(title: str, subtitle: str = "") -> None:
    sub = f"<p>{esc(subtitle)}</p>" if subtitle else ""
    st.markdown(f'<div class="page-head"><h1>{esc(title)}</h1>{sub}</div>', unsafe_allow_html=True)


def section_label(text: str) -> None:
    st.markdown(f'<div class="section-label">{esc(text)}</div>', unsafe_allow_html=True)


def chip(text: str, tone: str = "info") -> str:
    return f'<span class="chip {tone}">{esc(text)}</span>'


def panel(inner: str, title: str = "") -> str:
    head = f'<div class="panel-title">{esc(title)}</div>' if title else ""
    return f'<div class="panel">{head}{inner}</div>'


def style_figure(fig, height: int = 320):
    fig.update_layout(
        height=height, margin=dict(l=16, r=16, t=48, b=16),
        paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        font=dict(family="Inter, Segoe UI, sans-serif", size=12, color=INK),
        title=dict(font=dict(size=14, color=TEAL), x=0.02),
        legend_title_text="",
    )
    fig.update_xaxes(showgrid=False, linecolor=LINE)
    fig.update_yaxes(gridcolor="#EFECE4", linecolor=LINE)
    return fig


# ---- logo and header helpers ----------------------------------------------
def _logo_svg(size: int) -> str:
    """Original mining emblem: miner's hard hat with headlamp over crossed pickaxes."""
    return (f'<svg viewBox="0 0 64 64" width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">'
            f'<circle cx="32" cy="32" r="30" fill="{COPPER}"/>'
            '<circle cx="32" cy="32" r="27" fill="none" stroke="#F6D58E" stroke-width="1.5"/>'
            '<path d="M16 48 L48 16 M48 48 L16 16" stroke="#F3E7D3" stroke-width="4" stroke-linecap="round" fill="none"/>'
            '<path d="M35 13 Q55 7 57 27 Q49 17 35 13 Z M29 13 Q9 7 7 27 Q15 17 29 13 Z" fill="#F3E7D3"/>'
            '<path d="M17 40 Q17 21 32 21 Q47 21 47 40 Z" fill="#F6C24A"/>'
            '<rect x="13" y="39" width="38" height="6" rx="3" fill="#E0A52E"/>'
            '<rect x="29" y="21" width="6" height="19" fill="#E0A52E"/>'
            '<circle cx="32" cy="30" r="4" fill="#FFF6D6" stroke="#8A5A07" stroke-width="1"/></svg>')


def _custom_logo(size: int):
    """If you add your own logo as assets/logo.svg / .png / .jpg, it replaces the built-in emblem."""
    folder = Path(__file__).parent / "assets"
    for name, mime in (("logo.svg", "image/svg+xml"), ("logo.png", "image/png"),
                       ("logo.jpg", "image/jpeg"), ("logo.jpeg", "image/jpeg")):
        f = folder / name
        if f.is_file():
            data = base64.b64encode(f.read_bytes()).decode("ascii")
            return (f'<img src="data:{mime};base64,{data}" width="{size}" height="{size}" '
                    'style="object-fit:contain" alt="logo">')
    return None


def logo_html(size: int = 40, wordmark: bool = True) -> str:
    text = ('<div><div class="name">KHWEZI MINING</div>'
            '<div class="sub">Monitoring App</div></div>') if wordmark else ""
    return f'<div class="brand-row">{_custom_logo(size) or _logo_svg(size)}{text}</div>'


def refresh_now() -> None:
    st.session_state["last_refresh"] = datetime.now()


def last_updated_html() -> str:
    st.session_state.setdefault("last_refresh", datetime.now())
    stamp = st.session_state["last_refresh"].strftime("%d %b %Y, %H:%M")
    return f'<div class="stamp"><span class="live-dot"></span>Last updated {stamp}</div>'


def apply_login_theme() -> None:
    """Add the site photo behind the login panel (assets/login_bg.jpg). Falls back to the plain teal panel."""
    f = Path(__file__).parent / "assets" / "login_bg.jpg"
    if not f.is_file():
        return
    data = base64.b64encode(f.read_bytes()).decode("ascii")
    st.markdown(
        "<style>.login-brand { background-color: var(--deep); background-image:"
        " linear-gradient(180deg, rgba(8,40,38,.84) 0%, rgba(8,40,38,.66) 36%, rgba(8,40,38,.22) 66%, rgba(8,40,38,.62) 100%),"
        f' url("data:image/jpeg;base64,{data}");'
        " background-size: cover; background-position: 58% 80%; background-repeat: no-repeat; }"
        " .login-brand p, .login-brand li { text-shadow: 0 1px 3px rgba(0,0,0,.55); }"
        " @media (max-width: 700px) { .login-brand::before { content: ''; position: absolute; inset: 0;"
        " background: linear-gradient(180deg, rgba(8,40,38,.50) 0%, rgba(8,40,38,.62) 100%); }"
        " .login-brand > :not(.login-credit) { position: relative; z-index: 1; } }</style>",
        unsafe_allow_html=True)

