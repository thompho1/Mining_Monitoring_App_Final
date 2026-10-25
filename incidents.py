
from datetime import date, datetime, time

import pandas as pd
import plotly.express as px
import streamlit as st

from theme import page_header

from alerts import format_alert
from data import (
    ACTIONS,
    CAUSES,
    DEPARTMENTS,
    INCIDENT_TYPES,
    append_incident,
    ensure_sample_data,
    load_incidents,
    next_incident_id,
)
from ui import flash, show_flash

SEVERITIES = ["Low", "Medium", "High", "Critical"]
STATUSES = ["Open", "Under Investigation", "Closed"]
SEVERITY_COLOURS = {"Low": "#9ec5f4", "Medium": "#5b9bea", "High": "#2a78d6", "Critical": "#12427f"}
BLUE = "#2a78d6"
CATEGORY_FIELDS = {"Incident type": "incident_type", "Severity": "severity", "Department": "department",
                   "Shift": "shift", "Cause": "cause", "Status": "status", "Location": "location"}


def shift_for(hour: int) -> str:

    return "Day" if 6 <= hour < 18 else "Night"


def _filters(incidents: pd.DataFrame) -> pd.DataFrame:
    with st.expander("Search and filters", expanded=True):
        search = st.text_input("Search all fields", placeholder="e.g. Level 12, fatigue, INC-0042")
        r1 = st.columns(4)
        departments = r1[0].multiselect("Department", sorted(incidents["department"].unique()))
        types = r1[1].multiselect("Incident type", sorted(incidents["incident_type"].unique()))
        severities = r1[2].multiselect("Severity", SEVERITIES)
        shifts = r1[3].multiselect("Shift", ["Day", "Night"])
        r2 = st.columns(4)
        statuses = r2[0].multiselect("Status", STATUSES)
        injury = r2[1].selectbox("Injury", ["All", "Yes", "No"])
        lost_time = r2[2].selectbox("Lost-time injury", ["All", "Yes", "No"])
        first = incidents["date"].min().date()
        last = incidents["date"].max().date()
        period = r2[3].date_input("Period", value=(first, last), min_value=first, max_value=max(last, date.today()))

    df = incidents.copy()
    if search.strip():
        text = df.astype(str).agg(" ".join, axis=1).str.lower()
        df = df[text.str.contains(search.strip().lower(), regex=False)]
    for column, chosen in (("department", departments), ("incident_type", types),
                           ("severity", severities), ("shift", shifts), ("status", statuses)):
        if chosen:
            df = df[df[column].isin(chosen)]
    if injury != "All":
        df = df[df["injury"] == injury]
    if lost_time != "All":
        df = df[df["lost_time_injury"] == lost_time]
    if isinstance(period, (tuple, list)) and len(period) == 2:
        df = df[(df["date"].dt.date >= period[0]) & (df["date"].dt.date <= period[1])]
    return df


def _view_tab(df: pd.DataFrame) -> None:
    real = df[df["incident_type"] != "Near Miss"]
    m = st.columns(5)
    m[0].metric("Records found", len(df))
    m[1].metric("Safety incidents", len(real))
    m[2].metric("Near misses", len(df) - len(real))
    m[3].metric("High or critical", int(df["severity"].isin(["High", "Critical"]).sum()))
    m[4].metric("Lost-time injuries", int((df["lost_time_injury"] == "Yes").sum()))
    if df.empty:
        st.info("No incidents match the current search and filters.")
        return
    shown = df.sort_values("date", ascending=False).copy()
    shown["date"] = shown["date"].dt.strftime("%Y-%m-%d")
    st.dataframe(shown, hide_index=True)


def _categorise_tab(df: pd.DataFrame) -> None:
    label = st.selectbox("Categorise incidents by", list(CATEGORY_FIELDS))
    column = CATEGORY_FIELDS[label]
    if df.empty:
        st.info("No incidents match the current search and filters.")
        return
    counts = df.groupby(column).size().reset_index(name="incidents").sort_values("incidents", ascending=False)
    left, right = st.columns([1, 2])
    left.dataframe(counts.rename(columns={column: label}), hide_index=True)
    fig = px.bar(counts, x=column, y="incidents", text="incidents", labels={column: label},
                 color_discrete_sequence=[BLUE])
    fig.update_layout(showlegend=False, margin=dict(t=20))
    right.plotly_chart(fig)


def _trends_tab(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No incidents match the current search and filters.")
        return
    trend = df.copy()
    trend["month"] = trend["date"].dt.to_period("M").astype(str)
    monthly = trend.groupby("month").size().reset_index(name="incidents")
    fig = px.line(monthly, x="month", y="incidents", markers=True, title="Records per month",
                  color_discrete_sequence=[BLUE])
    fig.update_xaxes(type="category")
    st.plotly_chart(fig)

    left, right = st.columns(2)
    by_severity = trend.groupby(["month", "severity"]).size().reset_index(name="incidents")
    fig2 = px.bar(by_severity, x="month", y="incidents", color="severity", title="Monthly records by severity",
                  category_orders={"severity": SEVERITIES}, color_discrete_map=SEVERITY_COLOURS)
    fig2.update_xaxes(type="category")
    left.plotly_chart(fig2)

    trend["hour"] = trend["time"].str[:2].astype(int)
    by_hour = trend.groupby("hour").size().reset_index(name="incidents")
    fig3 = px.bar(by_hour, x="hour", y="incidents", title="Records by hour of day",
                  color_discrete_sequence=[BLUE])
    right.plotly_chart(fig3)

    by_shift = trend.groupby("shift").size()
    day, night = int(by_shift.get("Day", 0)), int(by_shift.get("Night", 0))
    st.write(f"Day shift recorded {day} and night shift {night} of the {len(trend)} records shown.")


def _validate(incident_id: str, existing: set, incident_type: str, injury: str, lost_time: str,
              location: str, action: str, when: datetime) -> list[str]:
    errors = []
    if not incident_id:
        errors.append("Incident ID is required.")
    elif not (incident_id.startswith("INC-") and incident_id[4:].isdigit()):
        errors.append("Incident ID must look like INC-0081.")
    elif incident_id in existing:
        errors.append(f"Incident ID {incident_id} already exists.")
    if when > datetime.now():
        errors.append("The incident date and time cannot be in the future.")
    if not location.strip():
        errors.append("Location is required.")
    if not action.strip():
        errors.append("Corrective action is required.")
    if lost_time == "Yes" and injury == "No":
        errors.append("A lost-time injury requires the injury status to be Yes.")
    if incident_type == "Near Miss" and injury == "Yes":
        errors.append("A near miss cannot involve an injury. Choose another incident type.")
    return errors


def _add_tab(incidents: pd.DataFrame) -> None:
    st.caption("The shift is set automatically from the time: day is 06:00-17:59, night is 18:00-05:59.")
    with st.form("add_incident"):
        a = st.columns(3)
        incident_id = a[0].text_input("Incident ID", value=next_incident_id(incidents))
        when_date = a[1].date_input("Date", value=date.today(), max_value=date.today())
        when_time = a[2].time_input("Time", value=time(8, 0), step=900)

        b = st.columns(3)
        department = b[0].selectbox("Department", DEPARTMENTS)
        location = b[1].text_input("Location", placeholder="e.g. Level 12 Stope")
        incident_type = b[2].selectbox("Incident type", INCIDENT_TYPES)

        c = st.columns(4)
        severity = c[0].selectbox("Severity", SEVERITIES)
        injury = c[1].selectbox("Injury", ["No", "Yes"])
        lost_time = c[2].selectbox("Lost-time injury", ["No", "Yes"])
        status = c[3].selectbox("Incident status", STATUSES)

        d = st.columns(2)
        cause = d[0].selectbox("Cause", CAUSES)
        action = d[1].text_input("Corrective action", placeholder="e.g. Area barricaded")

        submitted = st.form_submit_button("Save incident")

    if not submitted:
        return

    incident_id = incident_id.strip().upper()
    when = datetime.combine(when_date, when_time)
    errors = _validate(incident_id, set(incidents["incident_id"]), incident_type, injury, lost_time,
                       location, action, when)
    if errors:
        for message in errors:
            st.error(message)
        return

    record = {
        "incident_id": incident_id, "date": when_date.isoformat(), "time": when_time.strftime("%H:%M"),
        "shift": shift_for(when_time.hour), "location": location.strip(), "department": department,
        "incident_type": incident_type, "severity": severity, "injury": injury,
        "lost_time_injury": lost_time, "cause": cause, "corrective_action": action.strip(),
        "status": status,
    }
    append_incident(record)
    messages = [("success", f"Incident {incident_id} saved on the {record['shift'].lower()} shift.")]

    if severity == "Critical" and status != "Closed":
        alert = {"severity": "CRITICAL", "category": "Critical safety incident",
                 "subject_label": "Incident ID", "subject": incident_id, "parameter": "Severity",
                 "value": "Critical", "status": f"Incident {status} ({incident_type})",
                 "action": "Complete the investigation and implement corrective actions urgently."}
        messages.append(("error", "A critical safety incident alert has been generated."))
        messages.append(("code", format_alert(alert)))
    flash(*messages)


def show_incidents() -> None:
    ensure_sample_data()
    incidents = load_incidents()

    page_header("Safety Incident Database")
    show_flash()
    filtered = _filters(incidents)

    view, categorise, trends, add = st.tabs(["View and search", "Categorise and count", "Trends", "Add incident"])
    with view:
        _view_tab(filtered)
    with categorise:
        _categorise_tab(filtered)
    with trends:
        _trends_tab(filtered)
    with add:
        _add_tab(incidents)
