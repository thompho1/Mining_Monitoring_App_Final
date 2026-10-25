
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from theme import page_header

from data import (
    EQUIPMENT_TYPES,
    append_equipment,
    ensure_sample_data,
    load_equipment,
)
from monitoring import (
    TEMP_CRITICAL,
    TEMP_WARNING,
    VIB_CRITICAL,
    VIB_WARNING,
    availability,
    condition_message,
)
from ui import flash, show_flash

CONDITION_COLOURS = {"NORMAL": "#2e7d32", "WARNING": "#ef6c00", "CRITICAL": "#c62828"}
CONDITION_ICONS = {"NORMAL": "+", "WARNING": "!", "CRITICAL": "-"}
MAINTENANCE_STATUSES = ["Operational", "Due", "Overdue", "Under Maintenance"]


def _with_messages(equipment: pd.DataFrame) -> pd.DataFrame:
    df = equipment.copy()
    df["monitoring_message"] = [condition_message(t, v)[1] for t, v in zip(df["temperature"], df["vibration"])]
    return df


def _register_tab(equipment: pd.DataFrame) -> None:
    f = st.columns(3)
    types = f[0].multiselect("Equipment type", sorted(equipment["equipment_type"].unique()))
    conditions = f[1].multiselect("Condition", ["NORMAL", "WARNING", "CRITICAL"])
    search = f[2].text_input("Search", placeholder="ID or manufacturer")

    df = _with_messages(equipment)
    if types:
        df = df[df["equipment_type"].isin(types)]
    if conditions:
        df = df[df["condition"].isin(conditions)]
    if search.strip():
        key = search.strip().lower()
        df = df[df["equipment_id"].str.lower().str.contains(key, regex=False)
                | df["manufacturer"].str.lower().str.contains(key, regex=False)]

    m = st.columns(4)
    m[0].metric("Equipment shown", len(df))
    m[1].metric("Average availability", f"{df['availability'].mean():.1f}%" if len(df) else "n/a")
    m[2].metric("Total downtime", f"{int(df['downtime_hours'].sum())} h")
    m[3].metric("Total operating hours", f"{int(df['operating_hours'].sum())} h")
    if df.empty:
        st.info("No equipment matches the current filters.")
        return
    columns = ["equipment_id", "equipment_type", "manufacturer", "operating_hours", "downtime_hours",
               "availability", "temperature", "vibration", "fuel_consumption", "brake_status",
               "tyre_status", "engine_status", "maintenance_status", "alert_count", "condition"]
    st.dataframe(df[columns].sort_values("equipment_id"), hide_index=True,
                 column_config={"availability": st.column_config.NumberColumn("availability (%)", format="%.1f")})


def _monitoring_tab(equipment: pd.DataFrame) -> None:
    st.caption("Temperature and vibration limits are educational prototype thresholds only. "
               "They are not manufacturer or mine safety limits.")
    chosen = st.selectbox("Equipment", equipment["equipment_id"].tolist())
    row = equipment[equipment["equipment_id"] == chosen].iloc[0]
    status, message = condition_message(row["temperature"], row["vibration"])

    text = f"{CONDITION_ICONS[status]} {status}: {message}"
    if status == "CRITICAL":
        st.error(text)
    elif status == "WARNING":
        st.warning(text)
    else:
        st.success(text)

    c = st.columns(3)
    c[0].metric("Temperature", f"{row['temperature']:.1f} °C")
    c[1].metric("Vibration", f"{row['vibration']:.1f} mm/s")
    c[2].metric("Availability", f"{row['availability']:.1f}%")

    st.subheader("All equipment")
    fig = go.Figure()
    for condition, colour in CONDITION_COLOURS.items():
        part = equipment[equipment["condition"] == condition]
        fig.add_trace(go.Scatter(
            x=part["temperature"], y=part["vibration"], mode="markers", name=condition,
            text=part["equipment_id"], marker=dict(color=colour, size=10, line=dict(width=2, color="white")),
            hovertemplate="%{text}<br>%{x} °C, %{y} mm/s<extra></extra>"))
    fig.add_vline(x=TEMP_WARNING, line_dash="dot", line_color="#888")
    fig.add_vline(x=TEMP_CRITICAL, line_dash="dash", line_color="#888")
    fig.add_hline(y=VIB_WARNING, line_dash="dot", line_color="#888")
    fig.add_hline(y=VIB_CRITICAL, line_dash="dash", line_color="#888")
    fig.update_layout(xaxis_title="Temperature (°C)", yaxis_title="Vibration (mm/s)",
                      title="Temperature against vibration (dotted: warning, dashed: critical)")
    st.plotly_chart(fig)

    table = _with_messages(equipment)
    table = table[table["condition"] != "NORMAL"].sort_values("condition", ascending=False)
    if table.empty:
        st.success("All equipment is operating within the defined monitoring limits.")
    else:
        st.subheader("Equipment outside normal limits")
        st.dataframe(table[["equipment_id", "equipment_type", "temperature", "vibration", "condition",
                            "monitoring_message"]], hide_index=True)


def _validate(equipment_id: str, existing: set, operating: int, downtime: int, temperature: float,
              vibration: float) -> list[str]:
    errors = []
    parts = equipment_id.split("-")
    if not equipment_id:
        errors.append("Equipment ID is required.")
    elif not (len(parts) == 2 and parts[0].isalpha() and parts[1].isdigit()):
        errors.append("Equipment ID must look like TRK-012 (letters, a dash, then digits).")
    elif equipment_id in existing:
        errors.append(f"Equipment ID {equipment_id} already exists.")
    if operating + downtime == 0:
        errors.append("Operating hours and downtime cannot both be zero, because availability "
                      "cannot be calculated.")
    if not -20 <= temperature <= 200:
        errors.append("Temperature must be between -20 and 200 °C.")
    if not 0 <= vibration <= 50:
        errors.append("Vibration must be between 0 and 50 mm/s.")
    return errors


def _add_tab(equipment: pd.DataFrame) -> None:
    with st.form("add_equipment"):
        a = st.columns(3)
        equipment_id = a[0].text_input("Equipment ID", placeholder="e.g. TRK-004")
        equipment_type = a[1].selectbox("Equipment type", list(EQUIPMENT_TYPES))
        manufacturer = a[2].text_input("Manufacturer")

        b = st.columns(4)
        operating = b[0].number_input("Operating hours", min_value=0, max_value=100000, value=500, step=10)
        downtime = b[1].number_input("Downtime (hours)", min_value=0, max_value=100000, value=20, step=1)
        temperature = b[2].number_input("Temperature (°C)", min_value=-20.0, max_value=200.0, value=70.0, step=0.5)
        vibration = b[3].number_input("Vibration (mm/s)", min_value=0.0, max_value=50.0, value=3.0, step=0.1)

        c = st.columns(4)
        fuel = c[0].number_input("Fuel consumption (L/h)", min_value=0, max_value=1000, value=40, step=1)
        brake = c[1].selectbox("Brake status", ["OK", "Worn", "Faulty", "N/A"])
        tyre = c[2].selectbox("Tyre status", ["OK", "Worn", "Replace", "N/A"])
        engine = c[3].selectbox("Engine status", ["Normal", "Fault"])

        d = st.columns(2)
        maintenance = d[0].selectbox("Maintenance status", MAINTENANCE_STATUSES)
        alert_count = d[1].number_input("Alert count", min_value=0, max_value=1000, value=0, step=1)

        submitted = st.form_submit_button("Save equipment")

    if not submitted:
        return

    equipment_id = equipment_id.strip().upper()
    errors = _validate(equipment_id, set(equipment["equipment_id"]), int(operating), int(downtime),
                       float(temperature), float(vibration))
    if not manufacturer.strip():
        errors.append("Manufacturer is required.")
    if errors:
        for message in errors:
            st.error(message)
        return

    append_equipment({
        "equipment_id": equipment_id, "equipment_type": equipment_type, "manufacturer": manufacturer.strip(),
        "operating_hours": int(operating), "downtime_hours": int(downtime),
        "temperature": float(temperature), "vibration": float(vibration), "fuel_consumption": int(fuel),
        "brake_status": brake, "tyre_status": tyre, "engine_status": engine,
        "maintenance_status": maintenance, "alert_count": int(alert_count),
    })
    status, message = condition_message(float(temperature), float(vibration))
    kind = {"CRITICAL": "error", "WARNING": "warning"}.get(status, "info")
    flash(("success", f"Equipment {equipment_id} saved. Availability is "
                      f"{availability(int(operating), int(downtime)):.1f}%."),
          (kind, f"{status}: {message}"))


def show_equipment() -> None:
    ensure_sample_data()
    equipment = load_equipment()

    page_header("Equipment Data and Condition Monitoring")
    show_flash()
    register, monitoring, add = st.tabs(["Equipment register", "Condition monitoring", "Add equipment"])
    with register:
        _register_tab(equipment)
    with monitoring:
        _monitoring_tab(equipment)
    with add:
        _add_tab(equipment)
