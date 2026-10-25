# Khwezi Mining Monitoring App

A Streamlit application for monitoring mining health, safety and equipment data: worker safety,
incidents, risk assessment, equipment condition, maintenance and reporting, with role-based access.

All data in `data/` is sample (prototype/educational) data. Temperature and vibration limits are
prototype thresholds, not manufacturer or mine safety limits.

## Run

```
pip install -r requirements.txt
streamlit run app.py
```

Open the address Streamlit prints (usually http://localhost:8501). No internet connection is needed;
all images are stored in the `assets` folder.

## Login

Five demo accounts (user numbers 1 to 5) are defined in `build_default_users()` in `auth.py`:
Administrator, Safety Officer, Mining Engineer, Maintenance Engineer and Manager. Each role only
sees the pages allowed in `permissions.py`. After 3 failed attempts the login locks for 30 seconds.
To use your own accounts, point the `USERS_FILE` environment variable at a `users.json` file.

## Project layout

| File | Purpose |
|------|---------|
| `app.py` | Login screen, top header and tab navigation, page routing |
| `theme.py` | All styling (colours, CSS, logo, top bar, KPI cards) |
| `dashboard.py` | Operations overview: stat ledger, equipment status board, action rail, shift filter |
| `worker_safety.py`, `incidents.py`, `risk.py` | Safety pages |
| `equipment_page.py`, `maintenance.py` | Equipment pages |
| `reports.py`, `alerts.py`, `monitoring.py` | Reports, alerts and threshold logic |
| `auth.py`, `permissions.py`, `user_admin.py` | Authentication, roles, user management |
| `data.py`, `data/*.csv` | Data loading and sample data |

## Changing the look

Edit the colour constants at the top of `theme.py` (`TEAL`, `COPPER`, `DEEP`, and so on) and the page
colours in `.streamlit/config.toml`. The login panel text is in `show_login()` in `app.py`.

## Login photo

The login panel uses `assets/login_bg.jpg` (bulk ore sorter, Mogalakwena, South Africa; photo credit
Anglo American Platinum), tone-balanced and covered by a dark teal overlay so the text stays readable.
To change it, replace that file with another JPEG (landscape, about 1000 px wide or more). If the file
is missing, the login falls back to the plain teal panel. Check that you may use the photo and keep the
credit line if you submit or publish the project.

## Using your own logo

The app ships with an original mining emblem (miner's hard hat with headlamp over crossed pickaxes).
To use your own logo instead, create a folder called `assets` next to `app.py` and save your file there
as `logo.png`, `logo.svg` or `logo.jpg`. It replaces the built-in emblem on the login screen and header
automatically. A square image with a transparent background works best, because the header is dark teal.

## Dashboard charts (Plotly)

PPE compliance ring, incidents per month, incidents by department, incidents by type, incident
severity, asset condition, temperature vs vibration, and availability by equipment.
