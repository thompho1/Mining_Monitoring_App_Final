import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data import ensure_sample_data, load_equipment, load_incidents, load_workers
from theme import (CONDITION_COLOURS, COPPER, INK, LINE, MUTED, RISK_COLOURS, TEAL,
                   chip, esc, page_header, panel, section_label, style_figure)

SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
TILE_TINT = {"NORMAL": "#EAF5EF", "WARNING": "#FCF3E0", "CRITICAL": "#FBE9E7"}


def compute_kpis(workers: pd.DataFrame, incidents: pd.DataFrame, equipment: pd.DataFrame) -> dict:
    real_incidents = incidents[incidents["incident_type"] != "Near Miss"]
    under_maintenance = int((equipment["maintenance_status"] == "Under Maintenance").sum())
    return {
        "total_workers": len(workers), "total_incidents": len(real_incidents),
        "near_misses": int((incidents["incident_type"] == "Near Miss").sum()),
        "high_risk_observations": int(workers["risk_level"].isin(["High", "Critical"]).sum()),
        "ppe_compliance": (workers["ppe_compliant"] == "Yes").mean() * 100 if len(workers) else 0.0,
        "total_equipment": len(equipment), "equipment_available": len(equipment) - under_maintenance,
        "under_maintenance": under_maintenance,
        "equipment_alerts": int(equipment["condition"].isin(["WARNING", "CRITICAL"]).sum()),
        "critical_alerts": int((equipment["condition"] == "CRITICAL").sum()),
        "avg_availability": equipment["availability"].mean() if len(equipment) else 0.0,
    }


# ---------------------------------------------------------------- HTML builders
def _stat(label: str, value, tone: str = "") -> str:
    return f'<div class="lstat {tone}"><b>{value}</b><span>{esc(label)}</span></div>'


def _ledger(k: dict, shift: str) -> str:
    note = "" if shift == "All shifts" else f"<small>{esc(shift)} shift</small>"
    ppe = k["ppe_compliance"]
    ppe_tone = "ok" if ppe >= 90 else "warn" if ppe >= 75 else "crit"
    people = "".join([
        _stat("Workers", k["total_workers"]),
        _stat("Incidents", k["total_incidents"]),
        _stat("Near misses", k["near_misses"], "warn" if k["near_misses"] else ""),
        _stat("Elevated risk", k["high_risk_observations"], "crit" if k["high_risk_observations"] else "ok"),
        _stat("PPE compliance", f"{ppe:.1f}%", ppe_tone),
    ])
    assets = "".join([
        _stat("Tracked", k["total_equipment"]),
        _stat("Ready for use", k["equipment_available"], "ok"),
        _stat("In workshop", k["under_maintenance"]),
        _stat("On alert", k["equipment_alerts"], "warn" if k["equipment_alerts"] else "ok"),
        _stat("Critical", k["critical_alerts"], "crit" if k["critical_alerts"] else "ok"),
        _stat("Availability", f"{k['avg_availability']:.1f}%"),
    ])
    return (f'<div class="panel ledger"><div class="lrow"><div class="lname">People{note}</div>{people}</div>'
            f'<div class="lrow"><div class="lname">Assets</div>{assets}</div></div>')


def _board(equipment: pd.DataFrame) -> str:
    order = {"CRITICAL": 0, "WARNING": 1, "NORMAL": 2}
    eq = equipment.assign(_o=equipment["condition"].map(order).fillna(3)).sort_values(["_o", "equipment_id"])
    tiles = []
    for r in eq.itertuples():
        colour = CONDITION_COLOURS.get(r.condition, MUTED)
        tint = TILE_TINT.get(r.condition, "#F3F4F4")
        tag = ""
        if r.maintenance_status != "Operational":
            label = "Workshop" if r.maintenance_status == "Under Maintenance" else r.maintenance_status
            tag = f"<em>{esc(str(label))}</em>"
        tip = (f"{r.equipment_id} | {r.equipment_type} | {r.condition} | "
               f"temp {r.temperature:.1f} | vibration {r.vibration:.1f} | maintenance: {r.maintenance_status}")
        tiles.append(f'<div class="tile" title="{esc(tip)}" style="--c:{colour};--t:{tint}">'
                     f"<b>{esc(str(r.equipment_id))}</b><span>{esc(str(r.equipment_type))}</span>"
                     f'<div class="row"><i>{r.availability:.0f}%</i>{tag}</div></div>')
    counts = equipment["condition"].value_counts()
    legend = "".join(
        f'<span class="lg"><i style="background:{CONDITION_COLOURS[c]}"></i>{c.title()} {int(counts.get(c, 0))}</span>'
        for c in ("NORMAL", "WARNING", "CRITICAL"))
    note = '<span class="lg">Tile figure = availability %</span>'
    return panel(f'<div class="board">{"".join(tiles)}</div><div class="legend">{legend}{note}</div>',
                 "Equipment status board")


def _item(tone: str, title: str, sub: str) -> str:
    return f'<div class="item"><span class="dot {tone}"></span><div><b>{esc(title)}</b><small>{esc(sub)}</small></div></div>'


def _action_panel(equipment: pd.DataFrame, incidents: pd.DataFrame) -> str:
    items = []
    for r in equipment[equipment["condition"] == "CRITICAL"].itertuples():
        items.append(_item("crit", f"{r.equipment_id} is critical",
                           f"{r.equipment_type} | temp {r.temperature:.1f} | vibration {r.vibration:.1f}"))
    n_warn = int((equipment["condition"] == "WARNING").sum())
    if n_warn:
        items.append(_item("warn", f"{n_warn} assets on warning", "Review in Equipment data"))
    overdue = int((equipment["maintenance_status"] == "Overdue").sum())
    if overdue:
        items.append(_item("warn", f"{overdue} assets overdue for maintenance", "Schedule in Maintenance data"))
    if not items:
        items.append(_item("ok", "All assets within limits", "No equipment alerts"))

    open_inc = incidents[incidents["status"] != "Closed"].copy()
    if open_inc.empty:
        items.append(_item("ok", "No unresolved incidents", "Nothing open for this view"))
    else:
        open_inc["_s"] = open_inc["severity"].map(SEVERITY_ORDER).fillna(9)
        open_inc = open_inc.sort_values(["_s", "date"], ascending=[True, False])
        items.append(_item("info", f"{len(open_inc)} unresolved incidents", "Most severe shown first"))
        for r in open_inc.head(4).itertuples():
            tone = "crit" if r.severity in ("Critical", "High") else "warn"
            items.append(_item(tone, f"{r.incident_id} | {r.department}",
                               f"{r.incident_type} | {r.severity} | {r.status}"))
    return panel("".join(items), "Needs action")


def _risk_panel(workers: pd.DataFrame) -> str:
    counts = workers["risk_level"].value_counts()
    levels = ["Low", "Medium", "High", "Critical"]
    if int(counts.sum()) == 0:
        return panel('<div class="item"><div><small>No workers in this view</small></div></div>', "Worker risk profile")
    segs = "".join(f'<div class="seg" style="flex:{int(counts.get(l, 0))};background:{RISK_COLOURS[l]}"></div>'
                   for l in levels if int(counts.get(l, 0)))
    legend = "".join(f'<span class="lg"><i style="background:{RISK_COLOURS[l]}"></i>{l} {int(counts.get(l, 0))}</span>'
                     for l in levels)
    return panel(f'<div class="segbar">{segs}</div><div class="legend">{legend}</div>', "Worker risk profile")


def _ppe_ring(workers: pd.DataFrame):
    total = len(workers)
    ok = int((workers["ppe_compliant"] == "Yes").sum())
    pct = ok / total * 100 if total else 0.0
    fig = go.Figure(go.Pie(
        labels=["Compliant", "Not compliant"], values=[ok, total - ok], hole=0.74, sort=False,
        marker=dict(colors=[TEAL, LINE]), textinfo="none", hoverinfo="label+value"))
    style_figure(fig, 250)
    fig.update_layout(
        title_text="PPE compliance", showlegend=False,
        annotations=[
            dict(text=f"<b>{pct:.0f}%</b>", x=0.5, y=0.54, showarrow=False, font=dict(size=34, color=INK)),
            dict(text=f"{ok} of {total} workers", x=0.5, y=0.38, showarrow=False, font=dict(size=12, color=MUTED)),
        ])
    return fig


# ---------------------------------------------------------------------- page
def show_dashboard() -> None:
    ensure_sample_data()
    workers_all, incidents_all, equipment = load_workers(), load_incidents(), load_equipment()

    t1, t2 = st.columns([3, 2], vertical_alignment="center")
    with t1:
        page_header("Operations overview", "Health, safety and equipment status for the selected shift")
    shift = t2.radio("Shift", ["All shifts", "Day", "Night"], horizontal=True,
                     label_visibility="collapsed", key="dash_shift")

    if shift == "All shifts":
        workers, incidents = workers_all, incidents_all
    else:
        workers = workers_all[workers_all["shift"] == shift]
        incidents = incidents_all[incidents_all["shift"] == shift]
    k = compute_kpis(workers, incidents, equipment)

    # status chips (replaces alert boxes)
    chips = []
    if k["critical_alerts"]:
        chips.append(chip(f"{k['critical_alerts']} critical equipment alert{'s' if k['critical_alerts'] != 1 else ''}", "crit"))
    if k["high_risk_observations"]:
        chips.append(chip(f"{k['high_risk_observations']} worker{'s' if k['high_risk_observations'] != 1 else ''} at high or critical risk", "warn"))
    n_open = int((incidents["status"] != "Closed").sum())
    if n_open:
        chips.append(chip(f"{n_open} unresolved incident{'s' if n_open != 1 else ''}", "warn"))
    if not chips:
        chips.append(chip("All clear - no active alerts", "ok"))
    st.markdown(f'<div class="chips">{"".join(chips)}</div>', unsafe_allow_html=True)

    main, rail = st.columns([2.2, 1], gap="large")

    with main:
        st.markdown(_ledger(k, shift), unsafe_allow_html=True)
        st.markdown(_board(equipment), unsafe_allow_html=True)
        st.caption("Equipment is not assigned to a shift, so the board and asset figures do not change with the shift view. "
                   "Temperature and vibration limits are educational prototype thresholds, not manufacturer or mine safety limits.")

        section_label("Safety trends")
        c1, c2 = st.columns(2)
        real = incidents[incidents["incident_type"] != "Near Miss"].copy()
        if real.empty:
            c1.info("No safety incidents recorded for this view.")
        else:
            real["month"] = real["date"].dt.to_period("M").astype(str)
            monthly = real.groupby("month").size().reset_index(name="incidents")
            fig = px.area(monthly, x="month", y="incidents", title="Incidents per month")
            fig.update_traces(mode="lines+markers", line_color=TEAL, fillcolor="rgba(15,91,87,.16)")
            c1.plotly_chart(style_figure(fig, 320))

            by_dept = real.groupby("department").size().reset_index(name="incidents").sort_values("incidents")
            fig = px.bar(by_dept, x="incidents", y="department", orientation="h", title="Incidents by department")
            fig.update_traces(marker_color=COPPER)
            c2.plotly_chart(style_figure(fig, 320))

        c3, c4 = st.columns(2)
        if incidents.empty:
            c3.info("No incidents recorded for this view.")
        else:
            by_type = incidents.groupby("incident_type").size().reset_index(name="count").sort_values("count")
            fig = px.bar(by_type, x="count", y="incident_type", orientation="h",
                         title="Incidents by type (including near misses)")
            fig.update_traces(marker_color=TEAL)
            c3.plotly_chart(style_figure(fig, 320))

            sev = incidents.groupby("severity").size().reset_index(name="count")
            fig = px.pie(sev, names="severity", values="count", hole=0.6, color="severity",
                         color_discrete_map=RISK_COLOURS, title="Incident severity",
                         category_orders={"severity": ["Low", "Medium", "High", "Critical"]})
            fig.update_traces(textinfo="label+value", sort=False)
            c4.plotly_chart(style_figure(fig, 320))

        section_label("Equipment analytics")
        e1, e2 = st.columns(2)
        cond = equipment["condition"].value_counts().reset_index()
        cond.columns = ["condition", "count"]
        fig = px.pie(cond, names="condition", values="count", hole=0.6, color="condition",
                     color_discrete_map=CONDITION_COLOURS, title="Asset condition")
        fig.update_traces(textinfo="label+value")
        e1.plotly_chart(style_figure(fig, 320))

        fig = px.scatter(equipment, x="temperature", y="vibration", color="condition",
                         color_discrete_map=CONDITION_COLOURS, hover_name="equipment_id",
                         title="Temperature vs vibration")
        fig.update_traces(marker=dict(size=11, line=dict(width=1, color="#FFFFFF")))
        e2.plotly_chart(style_figure(fig, 320))

        ordered = equipment.sort_values("availability")
        fig = px.bar(ordered, x="equipment_id", y="availability", color="condition",
                     color_discrete_map=CONDITION_COLOURS, title="Availability by equipment (%)",
                     category_orders={"equipment_id": list(ordered["equipment_id"])})
        fig.update_xaxes(tickangle=-45)
        st.plotly_chart(style_figure(fig, 360))

    with rail:
        st.plotly_chart(_ppe_ring(workers))
        st.markdown(_action_panel(equipment, incidents), unsafe_allow_html=True)
        st.markdown(_risk_panel(workers), unsafe_allow_html=True)
