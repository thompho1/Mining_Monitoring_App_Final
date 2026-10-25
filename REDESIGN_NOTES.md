# Khwezi Mining Monitoring App - redesign notes

## What changed
- New palette: warm stone background, deep teal and copper (`theme.py`, `.streamlit/config.toml`).
- Original mining emblem (hard hat, headlamp, crossed pickaxes) drawn as SVG; drop `assets/logo.png` in to replace it.
- Login panel: site photo (`assets/login_bg.jpg`) under a graduated dark-teal overlay with a hazard-stripe edge;
  text contrast was measured at 5.1:1 or better on desktop and phone widths (WCAG AA needs 4.5:1).
- Navigation moved from a sidebar to a top header (logo, last-updated time, user, Refresh, Log out)
  plus a row of page tabs. Each role still only sees the tabs its permissions allow.
- Dashboard rebuilt around a different structure:
  - status chips (critical alerts, workers at risk, unresolved incidents) instead of alert boxes;
  - one ledger strip for People and Assets figures instead of a row of identical KPI cards;
  - an equipment status board, one tile per machine coloured by condition, with availability and maintenance flags;
  - a right-hand rail with the PPE compliance ring, a "Needs action" list and a worker risk bar;
  - eight Plotly charts: PPE ring, incident trend, incidents by department and by type, severity,
    asset condition, temperature vs vibration, and availability by equipment, with a Day / Night / All shifts filter.
- All other pages use the same page title style.

## Not changed
Authentication, lockout, role permissions, data files and KPI calculations are identical to the original.

## Notes
- Equipment has no shift in the data, so the board and asset figures do not change with the shift filter.
- Tab styling uses Streamlit container keys (Streamlit 1.40 or newer, see `requirements.txt`).
