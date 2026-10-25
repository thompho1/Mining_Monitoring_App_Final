
import json
import os
import re
from typing import Callable

import bcrypt
import pandas as pd
import streamlit as st

from theme import page_header

from auth import User
from permissions import ROLES, has_permission
from ui import flash, show_flash


def users_path() -> str:
    return os.environ.get("USERS_FILE", "users.json")


def save_users(users: dict, path: str | None = None) -> None:
    """Write all users to the JSON file used by auth.load_users_from_file."""
    path = path or users_path()
    raw = {str(number): {"password_hash": user.password_hash.decode("utf-8"), "role": user.role}
           for number, user in sorted(users.items())}
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as f:
        json.dump(raw, f, indent=2)
    os.replace(temporary, path)


def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def password_problems(password: str, confirm: str) -> list[str]:
    problems = []
    if len(password) < 8:
        problems.append("Password must be at least 8 characters long.")
    if not re.search(r"[a-z]", password):
        problems.append("Password needs a lowercase letter.")
    if not re.search(r"[A-Z]", password):
        problems.append("Password needs an uppercase letter.")
    if not re.search(r"\d", password):
        problems.append("Password needs a digit.")
    if not re.search(r"[^A-Za-z0-9]", password):
        problems.append("Password needs a special character such as # or !.")
    if password != confirm:
        problems.append("The two passwords do not match.")
    return problems


def administrator_count(users: dict) -> int:
    return sum(1 for user in users.values() if user.role == "Administrator")


def _commit(users: dict, on_change: Callable[[], None], message: str) -> None:
    save_users(users)
    on_change()
    flash(("success", message))


def _add_tab(users: dict, on_change: Callable[[], None]) -> None:
    with st.form("add_user", clear_on_submit=True):
        c = st.columns(2)
        number = c[0].number_input("User number", min_value=1, max_value=999999,
                                   value=max(users, default=0) + 1, step=1)
        role = c[1].selectbox("Role", ROLES)
        p = st.columns(2)
        password = p[0].text_input("Password", type="password")
        confirm = p[1].text_input("Confirm password", type="password")
        submitted = st.form_submit_button("Add user")
    if not submitted:
        return
    number = int(number)
    errors = []
    if number in users:
        errors.append(f"User number {number} already exists.")
    errors += password_problems(password, confirm)
    if errors:
        for message in errors:
            st.error(message)
        return
    new_users = dict(users)
    new_users[number] = User(user_number=number, password_hash=hash_password(password), role=role)
    _commit(new_users, on_change, f"User {number} added as {role}.")


def _edit_tab(users: dict, on_change: Callable[[], None]) -> None:
    number = st.selectbox("User", sorted(users), key="edit_user_pick")
    user = users[number]
    with st.form("edit_user"):
        role = st.selectbox("Role", ROLES, index=ROLES.index(user.role), key=f"role_{number}")
        st.caption("Leave the password fields empty to keep the current password.")
        p = st.columns(2)
        password = p[0].text_input("New password", type="password", key=f"pw_{number}")
        confirm = p[1].text_input("Confirm new password", type="password", key=f"pw2_{number}")
        submitted = st.form_submit_button("Save changes")
    if not submitted:
        return
    errors = []
    if user.role == "Administrator" and role != "Administrator" and administrator_count(users) == 1:
        errors.append("There must always be at least one Administrator.")
    if password or confirm:
        errors += password_problems(password, confirm)
    if role == user.role and not password:
        errors.append("Nothing to change.")
    if errors:
        for message in errors:
            st.error(message)
        return
    new_users = dict(users)
    new_users[number] = User(user_number=number,
                             password_hash=hash_password(password) if password else user.password_hash,
                             role=role)
    parts = []
    if role != user.role:
        parts.append(f"role changed to {role}")
    if password:
        parts.append("password reset")
    _commit(new_users, on_change, f"User {number}: " + " and ".join(parts) + ".")


def _delete_tab(users: dict, on_change: Callable[[], None]) -> None:
    number = st.selectbox("User to delete", sorted(users), key="delete_user_pick")
    confirmed = st.checkbox(f"I confirm that user {number} should be deleted", key=f"confirm_delete_{number}")
    if not st.button("Delete user"):
        return
    user = users[number]
    errors = []
    if number == st.session_state.get("user_number"):
        errors.append("You cannot delete the account you are logged in with.")
    if user.role == "Administrator" and administrator_count(users) == 1:
        errors.append("There must always be at least one Administrator.")
    if not confirmed:
        errors.append("Tick the confirmation box first.")
    if errors:
        for message in errors:
            st.error(message)
        return
    new_users = {n: u for n, u in users.items() if n != number}
    _commit(new_users, on_change, f"User {number} deleted.")


def show_user_admin(users: dict, on_change: Callable[[], None]) -> None:
    """`users` is the current user dictionary; `on_change` clears the app's cached copy."""
    if not has_permission(st.session_state.get("role"), "Manage users"):
        st.error("You do not have permission to manage users.")
        return

    page_header("Manage Users")
    show_flash()
    table = pd.DataFrame([{"user number": n, "role": u.role} for n, u in sorted(users.items())])
    st.dataframe(table, hide_index=True)

    add, edit, delete = st.tabs(["Add user", "Change role or reset password", "Delete user"])
    with add:
        _add_tab(users, on_change)
    with edit:
        _edit_tab(users, on_change)
    with delete:
        _delete_tab(users, on_change)
