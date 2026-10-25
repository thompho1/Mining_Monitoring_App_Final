
import os
import time

import streamlit as st

from auth import (
    LOCKOUT_SECONDS,
    MAX_ATTEMPTS,
    authenticate,
    build_default_users,
    load_users_from_file,
)
from dashboard import show_dashboard
from equipment_page import show_equipment
from incidents import show_incidents
from maintenance import show_maintenance
from permissions import allowed_functions, has_permission
from reports import show_reports
from risk import show_risk
from theme import apply_login_theme, apply_theme, last_updated_html, logo_html, page_header, refresh_now
from user_admin import show_user_admin
from worker_safety import show_worker_safety

st.set_page_config(page_title="Khwezi Mining Monitoring App", page_icon="\u26CF\uFE0F", layout="wide",
                   initial_sidebar_state="collapsed")
apply_theme()


@st.cache_resource
def get_users() -> dict:

    path = os.environ.get("USERS_FILE", "users.json")
    if os.path.exists(path):
        return load_users_from_file(path)
    return build_default_users()


def init_state() -> None:
    st.session_state.setdefault("user_number", None)
    st.session_state.setdefault("role", None)
    st.session_state.setdefault("attempts", 0)
    st.session_state.setdefault("locked_until", 0.0)


def show_login(users: dict) -> None:
    apply_login_theme()
    brand, _gap, form_col = st.columns([1.15, 0.08, 1])

    with brand:
        st.markdown(
            f"""
            <div class="login-brand">
              <div style="display:flex;align-items:center;gap:.8rem;color:#fff">{logo_html(52, wordmark=False)}<div class="login-tag">Khwezi Mining Monitoring App</div></div>
              <h1>Health, Safety and Equipment Monitoring</h1>
              <p>Know where your people and equipment stand before the shift starts.</p>
              <ul>
                <li>PPE compliance and worker risk at a glance</li>
                <li>Incident trends and alerts for every shift</li>
                <li>Equipment condition and maintenance status</li>
              </ul>
              <div class="login-credit">Bulk ore sorter, Mogalakwena, South Africa &middot; Photo: Anglo American Platinum</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with form_col:
        st.markdown("<div style='height:2.2rem'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div class="login-head"><h2>Sign in</h2>'
            '<p>Enter your credentials to access the monitoring system.</p></div>',
            unsafe_allow_html=True,
        )

        seconds_left = st.session_state.locked_until - time.time()
        if seconds_left > 0:
            st.error(f"Too many failed attempts. Try again in {int(seconds_left) + 1} seconds.")
            time.sleep(1)
            st.rerun()
            return

        with st.form("login_form"):
            user_number_text = st.text_input("User number", placeholder="e.g. 1")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in")

        st.caption("Authorised personnel only. Repeated failed attempts will lock the account temporarily.")

        if not submitted:
            return

        try:
            user_number = int(user_number_text)
        except ValueError:
            st.error("User number must be an integer.")
            role = None
        else:
            role = authenticate(users, user_number, password)

        if role is not None:
            st.session_state.user_number = user_number
            st.session_state.role = role
            st.session_state.attempts = 0
            st.rerun()
            return

        st.session_state.attempts += 1
        remaining = MAX_ATTEMPTS - st.session_state.attempts
        if remaining > 0:
            st.error(f"Access denied. {remaining} attempt(s) remaining.")
        else:
            st.session_state.attempts = 0
            st.session_state.locked_until = time.time() + LOCKOUT_SECONDS
            st.rerun()


# One placeholder page per function. Replace each with the real feature.
def page_placeholder(name: str) -> None:
    page_header(name)
    st.info(f"The '{name}' module will be implemented here.")


def _go(page: str) -> None:
    st.session_state.page = page


def _logout() -> None:
    for key in ("user_number", "role", "attempts", "locked_until", "page", "last_refresh"):
        st.session_state.pop(key, None)


def app_header(role: str) -> None:
    with st.container(key="appheader"):
        c1, c2, c3, c4, c5 = st.columns([3.1, 2.6, 2.1, 1, 1], vertical_alignment="center")
        c1.markdown(logo_html(36), unsafe_allow_html=True)
        c2.markdown(last_updated_html(), unsafe_allow_html=True)
        c3.markdown(f'<div class="user-chip"><b>User {st.session_state.user_number}</b><br>{role}</div>',
                    unsafe_allow_html=True)
        c4.button("Refresh", key="refresh_btn", on_click=refresh_now)
        c5.button("Log out", key="logout", on_click=_logout)


def show_app(users: dict) -> None:
    role = st.session_state.role
    options = allowed_functions(role)
    if not options:
        st.error("Your account has no access to any pages. Please contact an administrator.")
        st.button("Log out", key="logout_empty", on_click=_logout)
        return

    if st.session_state.get("page") not in options:
        st.session_state.page = options[0]
    choice = st.session_state.page

    app_header(role)
    with st.container(key="topnav"):
        for col, name in zip(st.columns(len(options)), options):
            col.button(name, key=f"nav_{name}", on_click=_go, args=(name,),
                       type="primary" if name == choice else "secondary")

    # Second layer of protection: check again before rendering the page.
    if not has_permission(role, choice):
        st.error("You do not have permission to view this page.")
        return

    if choice == "View dashboard":
        show_dashboard()
    elif choice == "Worker safety data":
        show_worker_safety()
    elif choice == "Safety incidents":
        show_incidents()
    elif choice == "Equipment data":
        show_equipment()
    elif choice == "Maintenance data":
        show_maintenance()
    elif choice == "Risk assessment":
        show_risk()
    elif choice == "Generate reports":
        show_reports()
    elif choice == "Manage users":
        show_user_admin(users, get_users.clear)
    else:
        page_placeholder(choice)


def main() -> None:
    init_state()
    users = get_users()
    if st.session_state.role is None:
        show_login(users)
    else:
        show_app(users)


main()
