
import pandas as pd
import streamlit as st

from theme import page_header

from data import (
    DEPARTMENTS,
    JOB_ROLES,
    append_worker,
    ensure_sample_data,
    load_workers,
    next_worker_id,
)
from monitoring import classify_risk, worker_warnings
from ui import flash, show_flash


def _with_warnings(workers: pd.DataFrame) -> pd.DataFrame:
    df = workers.copy()
    df["warnings"] = [", ".join(worker_warnings(row)) for _, row in df.iterrows()]
    df["warning_count"] = [len(worker_warnings(row)) for _, row in df.iterrows()]
    return df


def _monitor_tab(workers: pd.DataFrame) -> None:
    df = _with_warnings(workers)

    f1, f2, f3 = st.columns(3)
    departments = f1.multiselect("Department", sorted(df["department"].unique()))
    shifts = f2.multiselect("Shift", sorted(df["shift"].unique()))
    only_warnings = f3.checkbox("Show only workers with warnings")

    if departments:
        df = df[df["department"].isin(departments)]
    if shifts:
        df = df[df["shift"].isin(shifts)]
    if only_warnings:
        df = df[df["warning_count"] > 0]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Workers shown", len(df))
    m2.metric("With warnings", int((df["warning_count"] > 0).sum()))
    m3.metric("High or critical risk", int(df["risk_level"].isin(["High", "Critical"]).sum()))
    ppe = (df["ppe_compliant"] == "Yes").mean() * 100 if len(df) else 0.0
    m4.metric("PPE compliance", f"{ppe:.1f}%")

    urgent = df[df["risk_level"].isin(["High", "Critical"])]
    if len(urgent) > 0:
        st.warning("WARNING: high or critical risk workers: " + ", ".join(urgent["worker_id"]))

    columns = ["worker_id", "department", "job_role", "shift", "ppe_compliant", "training_status",
               "fatigue_level", "safety_observations", "near_misses", "previous_incidents",
               "risk_score", "risk_level", "warnings"]
    st.dataframe(df.sort_values("warning_count", ascending=False)[columns], hide_index=True)


def _validate(worker_id: str, existing_ids: set) -> list[str]:
    errors = []
    worker_id = worker_id.strip().upper()
    if not worker_id:
        errors.append("Worker ID is required.")
    elif not (worker_id[0] == "W" and worker_id[1:].isdigit()):
        errors.append("Worker ID must look like W061 (the letter W followed by digits).")
    elif worker_id in existing_ids:
        errors.append(f"Worker ID {worker_id} already exists.")
    return errors


def _add_tab(workers: pd.DataFrame) -> None:
    with st.form("add_worker", clear_on_submit=False):
        a1, a2, a3 = st.columns(3)
        worker_id = a1.text_input("Worker ID", value=next_worker_id(workers))
        department = a2.selectbox("Department", DEPARTMENTS)
        job_role = a3.selectbox("Job role", JOB_ROLES)

        b1, b2, b3 = st.columns(3)
        shift = b1.selectbox("Shift", ["Day", "Night"])
        ppe = b2.selectbox("PPE compliant", ["Yes", "No"])
        training = b3.selectbox("Safety training status", ["Valid", "Expired"])

        c1, c2, c3, c4 = st.columns(4)
        fatigue = c1.number_input("Fatigue level (1-10)", min_value=1, max_value=10, value=3, step=1)
        observations = c2.number_input("Safety observations", min_value=0, max_value=100, value=0, step=1)
        near_misses = c3.number_input("Near misses", min_value=0, max_value=100, value=0, step=1)
        previous = c4.number_input("Previous incidents", min_value=0, max_value=100, value=0, step=1)

        d1, d2 = st.columns(2)
        likelihood = d1.slider("Risk likelihood (1-5)", 1, 5, 2)
        consequence = d2.slider("Risk consequence (1-5)", 1, 5, 2)

        submitted = st.form_submit_button("Save worker record")

    if not submitted:
        return

    worker_id = worker_id.strip().upper()
    errors = _validate(worker_id, set(workers["worker_id"]))
    if errors:
        for message in errors:
            st.error(message)
        return

    record = {
        "worker_id": worker_id, "department": department, "job_role": job_role, "shift": shift,
        "ppe_compliant": ppe, "training_status": training, "fatigue_level": int(fatigue),
        "safety_observations": int(observations), "near_misses": int(near_misses),
        "previous_incidents": int(previous), "likelihood": int(likelihood),
        "consequence": int(consequence),
    }
    append_worker(record)

    score, level = classify_risk(record["likelihood"], record["consequence"])
    record["risk_level"] = level
    messages = [("success", f"Worker {worker_id} saved. Risk score {score} ({level}).")]
    messages += [("warning", f"WARNING: {message}") for message in worker_warnings(record)]
    flash(*messages)


def show_worker_safety() -> None:
    ensure_sample_data()
    workers = load_workers()

    page_header("Worker Health and Safety")
    show_flash()
    st.caption("Warning thresholds are educational prototype values, not mine safety limits.")

    monitor, add = st.tabs(["Monitor workers", "Record a worker"])
    with monitor:
        _monitor_tab(workers)
    with add:
        _add_tab(workers)
