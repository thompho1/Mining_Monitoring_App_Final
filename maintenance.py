
import pandas as pd
import plotly.express as px
import streamlit as st

from theme import page_header

from data import ensure_sample_data, load_equipment, update_equipment
from monitoring import (
    EXCESSIVE_DOWNTIME_HOURS,
    LOW_AVAILABILITY,
    REPEATED_ALERT_COUNT,
    availability,
    maintenance_flags,
    maintenance_priority,
)
from ui import flash, show_flash

CATEGORIES = ["Due for maintenance", "Overdue", "Under maintenance",
              "Excessive downtime", "Repeated alerts", "Low availability"]
MAINTENANCE_STATUSES = ["Operational", "Due", "Overdue", "Under Maintenance"]
BLUE = "#2a78d6"


def _register_tab(df: pd.DataFrame) -> None:
    chosen = st.multiselect("Show equipment in these categories (empty shows all)", CATEGORIES)
    shown = df
    if chosen:
        shown = df[df["flag_list"].apply(lambda flags: any(c in flags for c in chosen))]
    if shown.empty:
        st.info("No equipment falls in the selected categories.")
        return
    columns = ["equipment_id", "equipment_type", "maintenance_status", "operating_hours", "downtime_hours",
               "availability", "alert_count", "condition", "categories", "priority"]
    st.dataframe(shown.sort_values("priority", ascending=False)[columns], hide_index=True,
                 column_config={"availability": st.column_config.NumberColumn("availability (%)", format="%.1f"),
                                "priority": st.column_config.NumberColumn("priority score")})
    st.caption("The priority score adds points for a critical or warning condition, overdue or due "
               "maintenance, excessive downtime, repeated alerts and low availability. Higher means sooner.")


def _update_tab(df: pd.DataFrame) -> None:
    chosen = st.selectbox("Equipment", df["equipment_id"].tolist(), key="maintenance_pick")
    row = df[df["equipment_id"] == chosen].iloc[0]
    st.write(f"Current status: **{row['maintenance_status']}**. Operating {int(row['operating_hours'])} h, "
             f"downtime {int(row['downtime_hours'])} h, availability {row['availability']:.1f}%.")

    with st.form("update_maintenance"):
        status = st.selectbox("Maintenance status", MAINTENANCE_STATUSES,
                              index=MAINTENANCE_STATUSES.index(row["maintenance_status"]),
                              key=f"status_{chosen}")
        c = st.columns(2)
        add_operating = c[0].number_input("Operating hours to add", min_value=0, max_value=10000, value=0,
                                          step=1, key=f"op_{chosen}")
        add_downtime = c[1].number_input("Downtime hours to add", min_value=0, max_value=10000, value=0,
                                         step=1, key=f"down_{chosen}")
        submitted = st.form_submit_button("Update maintenance record")

    if not submitted:
        return
    new_operating = int(row["operating_hours"]) + int(add_operating)
    new_downtime = int(row["downtime_hours"]) + int(add_downtime)
    update_equipment(chosen, {"maintenance_status": status, "operating_hours": new_operating,
                              "downtime_hours": new_downtime})
    flash(("success", f"{chosen} updated: status {status}, availability now "
                      f"{availability(new_operating, new_downtime):.1f}%."))


def _charts_tab(df: pd.DataFrame) -> None:
    ranked = df.sort_values("availability")
    fig = px.bar(ranked, x="availability", y="equipment_id", orientation="h",
                 title="Availability by equipment (%)", color_discrete_sequence=[BLUE])
    fig.add_vline(x=LOW_AVAILABILITY, line_dash="dash", line_color="#c62828",
                  annotation_text=f"Low availability limit ({LOW_AVAILABILITY:.0f}%)")
    fig.update_layout(height=max(400, 22 * len(df)), yaxis_title=None)
    st.plotly_chart(fig)

    by_type = df.groupby("equipment_type")["downtime_hours"].sum().reset_index().sort_values(
        "downtime_hours", ascending=False)
    fig2 = px.bar(by_type, x="equipment_type", y="downtime_hours", text="downtime_hours",
                  title="Total downtime by equipment type (hours)", color_discrete_sequence=[BLUE])
    st.plotly_chart(fig2)


def show_maintenance() -> None:
    ensure_sample_data()
    df = load_equipment()
    df["flag_list"] = [maintenance_flags(row) for _, row in df.iterrows()]
    df["categories"] = [", ".join(flags) for flags in df["flag_list"]]
    df["priority"] = [maintenance_priority(row) for _, row in df.iterrows()]

    page_header("Equipment Maintenance Monitoring")
    show_flash()

    cols = st.columns(6)
    for col, category in zip(cols, CATEGORIES):
        col.metric(category, int(sum(category in flags for flags in df["flag_list"])))
    st.caption("Availability = operating time / (operating time + downtime) x 100. Prototype limits: excessive "
               f"downtime is more than {EXCESSIVE_DOWNTIME_HOURS} h, repeated alerts means {REPEATED_ALERT_COUNT} "
               f"or more, and low availability is below {LOW_AVAILABILITY:.0f}%.")

    register, update, charts = st.tabs(["Maintenance register", "Update a record", "Availability and downtime"])
    with register:
        _register_tab(df)
    with update:
        _update_tab(df)
    with charts:
        _charts_tab(df)
