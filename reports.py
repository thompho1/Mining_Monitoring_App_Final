
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from theme import page_header

from alerts import alerts_table, format_alert, generate_alerts
from data import ensure_sample_data, load_equipment, load_incidents, load_workers
from monitoring import (
    EXCESSIVE_DOWNTIME_HOURS,
    FATIGUE_ALERT,
    LOW_AVAILABILITY,
    PPE_COMPLIANCE_MIN,
    maintenance_priority,
)
from permissions import has_permission

BLUE = "#2a78d6"
SEVERITY_ICONS = {"CRITICAL": "✖ CRITICAL", "WARNING": "▲ WARNING"}



def _plural(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def _equipment_extremes(column: str, label: str, ascending: bool = False, unit: str = "", decimals: int = 0):
    def answer(data):
        eq = data["equipment"].sort_values(column, ascending=ascending).head(10).copy()
        eq[column] = eq[column].round(decimals)
        top = eq.iloc[0]
        text = f"{top['equipment_id']} ({top['equipment_type']}) has the {label}: {top[column]:.{decimals}f}{unit}."
        return text, eq[["equipment_id", "equipment_type", column]], ("equipment_id", column)
    return answer


def q_incident_count(data):
    inc = data["incidents"]
    real = inc[inc["incident_type"] != "Near Miss"]
    monthly = real.assign(month=real["date"].dt.to_period("M").astype(str)).groupby("month").size() \
        .reset_index(name="incidents")
    return (f"{len(real)} safety incidents occurred in the selected period "
            f"(near misses are counted separately: {len(inc) - len(real)})."), monthly, ("month", "incidents")


def _count_by(column: str, exclude_near_miss: bool = False, noun: str = "incidents"):
    def answer(data):
        inc = data["incidents"]
        if exclude_near_miss:
            inc = inc[inc["incident_type"] != "Near Miss"]
        if inc.empty:
            return "No incidents in the selected period.", None, None
        counts = inc.groupby(column).size().reset_index(name="incidents").sort_values("incidents", ascending=False)
        top = counts.iloc[0]
        return (f"{top[column]} has the most {noun} with {int(top['incidents'])} of {len(inc)} "
                f"({top['incidents'] / len(inc) * 100:.0f}%)."), counts, (column, "incidents")
    return answer


def q_shift(data):
    text, counts, chart = _count_by("shift", True)(data)
    if counts is None:
        return text, counts, chart
    by = dict(zip(counts["shift"], counts["incidents"]))
    day, night = by.get("Day", 0), by.get("Night", 0)
    if day == night:
        verdict = "Day and night shifts record the same number of incidents."
    else:
        busier = "Night" if night > day else "Day"
        verdict = f"{busier} shift records more incidents (day {day}, night {night}). This is a count only: " \
                  "it does not account for how many people work each shift."
    return verdict, counts, chart


def q_near_misses(data):
    inc = data["incidents"]
    near = inc[inc["incident_type"] == "Near Miss"]
    counts = near.groupby("department").size().reset_index(name="near_misses") \
        .sort_values("near_misses", ascending=False)
    return f"{len(near)} near misses were recorded in the selected period.", counts, ("department", "near_misses")


def q_high_critical(data):
    inc = data["incidents"]
    high = inc[inc["severity"].isin(["High", "Critical"])]
    counts = high.groupby("severity").size().reset_index(name="incidents")
    return (f"{len(high)} incidents are classified as high or critical "
            f"({int((high['severity'] == 'Critical').sum())} critical)."), counts, ("severity", "incidents")


def q_attention_incidents(data):
    inc = data["incidents"]
    urgent = inc[inc["severity"].isin(["High", "Critical"]) & (inc["status"] != "Closed")].copy()
    urgent["date"] = urgent["date"].dt.strftime("%Y-%m-%d")
    return (f"{len(urgent)} high or critical incidents are not yet closed and need immediate attention.",
            urgent[["incident_id", "date", "department", "incident_type", "severity", "status"]], None)


def q_ppe(data):
    w = data["workers"]
    overall = (w["ppe_compliant"] == "Yes").mean() * 100
    by = (w.assign(compliant=w["ppe_compliant"] == "Yes").groupby("department")["compliant"].mean() * 100) \
        .round(1).reset_index(name="ppe_compliance_percent")
    by = by.sort_values("ppe_compliance_percent")
    return f"{overall:.1f}% of workers comply with PPE requirements.", by, ("department", "ppe_compliance_percent")


def q_department_risk(data):
    w = data["workers"]
    by = w.groupby("department").agg(average_risk_score=("risk_score", "mean"),
                                     high_or_critical=("risk_level", lambda s: int(s.isin(["High", "Critical"]).sum()))) \
        .reset_index().sort_values("average_risk_score", ascending=False)
    by["average_risk_score"] = by["average_risk_score"].round(1)
    top = by.iloc[0]
    return (f"{top['department']} has the highest average risk score ({top['average_risk_score']}) "
            f"based on worker risk assessments."), by, ("department", "average_risk_score")


def q_management_indicators(data):
    w = data["workers"]
    ppe = (w["ppe_compliant"] == "Yes").mean() * 100
    rows = [
        ("PPE compliance (%)", f"{ppe:.1f}", f"at least {PPE_COMPLIANCE_MIN:.0f}", ppe < PPE_COMPLIANCE_MIN),
        ("Workers with expired training", int((w["training_status"] != "Valid").sum()), "0",
         (w["training_status"] != "Valid").any()),
        (f"Workers with fatigue of {FATIGUE_ALERT} or more", int((w["fatigue_level"] >= FATIGUE_ALERT).sum()),
         "0", (w["fatigue_level"] >= FATIGUE_ALERT).any()),
        ("Workers at high or critical risk", int(w["risk_level"].isin(["High", "Critical"]).sum()), "0",
         w["risk_level"].isin(["High", "Critical"]).any()),
    ]
    table = pd.DataFrame([{"indicator": r[0], "value": str(r[1]), "target": r[2],
                           "needs intervention": "Yes" if r[3] else "No"} for r in rows])
    return f"{int((table['needs intervention'] == 'Yes').sum())} of {len(table)} indicators need management intervention.", table, None


def q_downtime_type(data):
    eq = data["equipment"]
    by = eq.groupby("equipment_type").agg(total_downtime_hours=("downtime_hours", "sum"),
                                          average_downtime_hours=("downtime_hours", "mean")) \
        .reset_index().sort_values("total_downtime_hours", ascending=False)
    by["average_downtime_hours"] = by["average_downtime_hours"].round(1)
    top = by.iloc[0]
    return (f"{top['equipment_type']} has the highest total downtime ({int(top['total_downtime_hours'])} h)."), by, \
        ("equipment_type", "total_downtime_hours")


def q_average_availability(data):
    eq = data["equipment"]
    by = eq.groupby("equipment_type")["availability"].mean().round(1).reset_index() \
        .sort_values("availability")
    return f"Average equipment availability is {eq['availability'].mean():.1f}%.", by, ("equipment_type", "availability")


def q_normal(data):
    eq = data["equipment"]
    counts = eq["condition"].value_counts().reset_index()
    counts.columns = ["condition", "equipment"]
    return (f"{(eq['condition'] == 'NORMAL').mean() * 100:.1f}% of monitored equipment is operating normally "
            f"({int((eq['condition'] == 'NORMAL').sum())} of {len(eq)})."), counts, ("condition", "equipment")


def q_inspection(data):
    eq = data["equipment"]
    critical = eq[eq["condition"] == "CRITICAL"]
    verb = "is" if len(critical) == 1 else "are"
    return (f"{_plural(len(critical), 'equipment item', 'equipment items')} {verb} in a CRITICAL condition "
            f"and {'requires' if len(critical) == 1 else 'require'} immediate inspection."), \
        critical[["equipment_id", "equipment_type", "temperature", "vibration"]], None


def q_maintenance_needed(data):
    eq = data["equipment"]
    needed = eq[eq["maintenance_status"].isin(["Due", "Overdue"])]
    verb = "requires" if len(needed) == 1 else "require"
    return (f"{_plural(len(needed), 'equipment item', 'equipment items')} {verb} maintenance "
            f"({int((needed['maintenance_status'] == 'Overdue').sum())} overdue)."), needed[["equipment_id", "equipment_type", "maintenance_status", "alert_count"]], None


def q_overdue(data):
    eq = data["equipment"]
    overdue = eq[eq["maintenance_status"] == "Overdue"]
    verb = "is" if len(overdue) == 1 else "are"
    return f"{_plural(len(overdue), 'equipment item', 'equipment items')} {verb} overdue for maintenance.", \
        overdue[["equipment_id", "equipment_type", "downtime_hours", "alert_count"]], None


def q_priority(data):
    eq = data["equipment"].copy()
    eq["priority_score"] = [maintenance_priority(r) for _, r in eq.iterrows()]
    top = eq.sort_values(["priority_score", "alert_count"], ascending=False).head(10)
    return (f"{top.iloc[0]['equipment_id']} should receive maintenance priority "
            f"(score {int(top.iloc[0]['priority_score'])})."), \
        top[["equipment_id", "equipment_type", "condition", "maintenance_status", "priority_score"]], \
        ("equipment_id", "priority_score")


def q_active_alerts(data):
    alerts = data["alerts"]
    critical = [a for a in alerts if a["severity"] == "CRITICAL"]
    table = alerts_table(critical)
    return f"{len(critical)} critical alerts are currently active ({len(alerts)} alerts in total).", table, None


# (topic, question, permission needed, answer function)
QUESTIONS = [
    ("Health and safety incidents", "How many safety incidents occurred during the selected period?", "Safety incidents", q_incident_count),
    ("Health and safety incidents", "Which department has the highest number of incidents?", "Safety incidents", _count_by("department", True)),
    ("Health and safety incidents", "Which shift records the most incidents? Is there a difference between day and night?", "Safety incidents", q_shift),
    ("Health and safety incidents", "How many near misses have been recorded?", "Safety incidents", q_near_misses),
    ("Health and safety incidents", "Which incident types occur most frequently?", "Safety incidents", _count_by("incident_type", False, "records")),
    ("Health and safety incidents", "How many incidents are classified as high or critical?", "Safety incidents", q_high_critical),
    ("Health and safety incidents", "What are the most common causes of safety incidents?", "Safety incidents", _count_by("cause", True)),
    ("Health and safety incidents", "Which safety conditions require immediate attention?", "Safety incidents", q_attention_incidents),
    ("Workers", "What percentage of workers comply with PPE requirements?", "Worker safety data", q_ppe),
    ("Workers", "Which departments have the highest safety risk?", "Worker safety data", q_department_risk),
    ("Workers", "Which safety indicators require management intervention?", "Worker safety data", q_management_indicators),
    ("Equipment", "Which equipment has the highest downtime?", "Equipment data", _equipment_extremes("downtime_hours", "highest downtime", False, " h")),
    ("Equipment", "Which equipment has the lowest availability?", "Equipment data", _equipment_extremes("availability", "lowest availability", True, "%", 1)),
    ("Equipment", "Which equipment has the highest vibration?", "Equipment data", _equipment_extremes("vibration", "highest vibration", False, " mm/s", 1)),
    ("Equipment", "Which equipment has the highest operating temperature?", "Equipment data", _equipment_extremes("temperature", "highest temperature", False, " °C", 1)),
    ("Equipment", "Which equipment has generated the most alerts?", "Equipment data", _equipment_extremes("alert_count", "most alerts", False, " alerts")),
    ("Equipment", "Which equipment type has the highest downtime?", "Equipment data", q_downtime_type),
    ("Equipment", "What is the average equipment availability?", "Equipment data", q_average_availability),
    ("Equipment", "What percentage of monitored equipment is operating normally?", "Equipment data", q_normal),
    ("Equipment", "Which equipment requires immediate inspection?", "Equipment data", q_inspection),
    ("Maintenance", "Which equipment requires maintenance?", "Maintenance data", q_maintenance_needed),
    ("Maintenance", "Which equipment is overdue for maintenance?", "Maintenance data", q_overdue),
    ("Maintenance", "Which equipment should receive maintenance priority?", "Maintenance data", q_priority),
    ("Alerts", "How many critical alerts are currently active?", None, q_active_alerts),
]


def available_questions(role: str) -> list[tuple]:
    return [q for q in QUESTIONS if q[2] is None or has_permission(role, q[2])]


# ---------------------------------------------------------------- recommendations and summary

def recommendations(data: dict, role: str) -> list[str]:
    """Generate plain-language recommendations from the monitoring results the role may see."""
    out = []
    eq, workers, inc = data["equipment"], data["workers"], data["incidents"]
    if has_permission(role, "Equipment data"):
        critical = eq[eq["condition"] == "CRITICAL"]["equipment_id"].tolist()
        if critical:
            out.append("Inspect the following equipment immediately and apply maintenance and safety "
                       "procedures: " + ", ".join(critical) + ".")
        long_downtime = eq[eq["downtime_hours"] > EXCESSIVE_DOWNTIME_HOURS]["equipment_id"].tolist()
        if long_downtime:
            out.append(f"Review the causes of downtime above {EXCESSIVE_DOWNTIME_HOURS} h for: "
                       + ", ".join(long_downtime) + ".")
        low = eq[eq["availability"] < LOW_AVAILABILITY]["equipment_id"].tolist()
        if low:
            out.append(f"Investigate availability below {LOW_AVAILABILITY:.0f}% for: " + ", ".join(low) + ".")
    if has_permission(role, "Maintenance data"):
        overdue = eq[eq["maintenance_status"] == "Overdue"]["equipment_id"].tolist()
        if overdue:
            out.append("Schedule the overdue maintenance for: " + ", ".join(overdue) + ".")
    if has_permission(role, "Worker safety data"):
        for department, group in workers.groupby("department"):
            compliance = (group["ppe_compliant"] == "Yes").mean() * 100
            if compliance < PPE_COMPLIANCE_MIN:
                out.append(f"Enforce PPE requirements in {department} (compliance {compliance:.0f}%).")
        tired = int((workers["fatigue_level"] >= FATIGUE_ALERT).sum())
        if tired:
            out.append(f"Review rosters and rest periods for the {tired} workers with a fatigue level of "
                       f"{FATIGUE_ALERT} or more.")
        risky = int(workers["risk_level"].isin(["High", "Critical"]).sum())
        if risky:
            out.append(f"Implement risk reduction measures for the {risky} workers assessed as high or "
                       "critical risk.")
        expired = int((workers["training_status"] != "Valid").sum())
        if expired:
            out.append(f"Renew safety training for the {expired} workers whose training has expired.")
    if has_permission(role, "Safety incidents"):
        open_critical = inc[(inc["severity"] == "Critical") & (inc["status"] != "Closed")]["incident_id"].tolist()
        if open_critical:
            out.append("Complete the investigation and corrective actions for open critical incidents: "
                       + ", ".join(open_critical) + ".")
        real = inc[inc["incident_type"] != "Near Miss"]
        if len(real) > 0:
            cause = real["cause"].value_counts()
            out.append(f"The most common cause of incidents is '{cause.index[0]}' ({int(cause.iloc[0])} of "
                       f"{len(real)}); target preventive controls at this cause.")
    if not out:
        out.append("No action is required for the data this role can access. Continue routine monitoring.")
    return out


def summary_text(data: dict, role: str, user_number) -> str:
    inc, workers, eq = data["incidents"], data["workers"], data["equipment"]
    lines = ["KHWEZI MINING MONITORING APP",
             "HEALTH, SAFETY AND EQUIPMENT MONITORING REPORT",
             f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
             f"Prepared for: user {user_number} ({role})", ""]
    if has_permission(role, "Safety incidents"):
        real = inc[inc["incident_type"] != "Near Miss"]
        lines += ["SAFETY INCIDENTS",
                  f"Total safety incidents: {len(real)}",
                  f"Near misses: {len(inc) - len(real)}",
                  f"High or critical incidents: {int(inc['severity'].isin(['High', 'Critical']).sum())}",
                  f"Lost-time injuries: {int((inc['lost_time_injury'] == 'Yes').sum())}", ""]
    if has_permission(role, "Worker safety data"):
        lines += ["WORKER SAFETY",
                  f"Total workers: {len(workers)}",
                  f"PPE compliance: {(workers['ppe_compliant'] == 'Yes').mean() * 100:.1f}%",
                  f"High-risk observations: {int(workers['risk_level'].isin(['High', 'Critical']).sum())}", ""]
    if has_permission(role, "Equipment data"):
        lines += ["EQUIPMENT",
                  f"Total equipment: {len(eq)}",
                  f"Operating normally: {(eq['condition'] == 'NORMAL').mean() * 100:.1f}%",
                  f"Warning: {int((eq['condition'] == 'WARNING').sum())}",
                  f"Critical: {int((eq['condition'] == 'CRITICAL').sum())}",
                  f"Average availability: {eq['availability'].mean():.1f}%", ""]
    if has_permission(role, "Maintenance data"):
        lines += ["MAINTENANCE",
                  f"Due: {int((eq['maintenance_status'] == 'Due').sum())}",
                  f"Overdue: {int((eq['maintenance_status'] == 'Overdue').sum())}",
                  f"Under maintenance: {int((eq['maintenance_status'] == 'Under Maintenance').sum())}", ""]
    alerts = data["alerts"]
    lines += ["ALERTS",
              f"Critical alerts: {sum(a['severity'] == 'CRITICAL' for a in alerts)}",
              f"Warning alerts: {sum(a['severity'] == 'WARNING' for a in alerts)}", "", "RECOMMENDATIONS"]
    lines += [f"{i}. {text}" for i, text in enumerate(recommendations(data, role), 1)]
    lines += ["", "Note: temperature, vibration and other limits are educational prototype thresholds only."]
    return "\n".join(lines)


# ---------------------------------------------------------------- tabs

def _alerts_tab(alerts: list[dict]) -> None:
    if not alerts:
        st.success("No alerts are active for the data your role can access.")
        return
    critical = sum(a["severity"] == "CRITICAL" for a in alerts)
    m = st.columns(3)
    m[0].metric("Total alerts", len(alerts))
    m[1].metric("Critical", critical)
    m[2].metric("Warning", len(alerts) - critical)

    f = st.columns(2)
    severities = f[0].multiselect("Severity", ["CRITICAL", "WARNING"])
    categories = f[1].multiselect("Category", sorted({a["category"] for a in alerts}))
    shown = [a for a in alerts if (not severities or a["severity"] in severities)
             and (not categories or a["category"] in categories)]
    if not shown:
        st.info("No alerts match the selected filters.")
        return

    table = alerts_table(shown)
    table["severity"] = table["severity"].map(SEVERITY_ICONS)
    st.dataframe(table, hide_index=True)

    labels = [f"{a['severity']} | {a['category']} | {a['subject']}" for a in shown]
    pick = st.selectbox("View an alert in the monitoring alert format", labels)
    text = format_alert(shown[labels.index(pick)])
    st.code(text, language=None)

    everything = "\n\n".join(format_alert(a) for a in shown)
    d = st.columns(2)
    d[0].download_button("Download these alerts (text)", everything, "khwezi_alerts.txt", "text/plain")
    d[1].download_button("Download alert table (CSV)", alerts_table(shown).to_csv(index=False),
                         "khwezi_alerts.csv", "text/csv")


def _analysis_tab(data: dict, role: str) -> None:
    questions = available_questions(role)
    incidents = data["incidents"]
    if has_permission(role, "Safety incidents") and not incidents.empty:
        first, last = incidents["date"].min().date(), incidents["date"].max().date()
        period = st.date_input("Period for incident questions", value=(first, last), min_value=first,
                               max_value=max(last, date.today()))
        if isinstance(period, (tuple, list)) and len(period) == 2:
            data = dict(data)
            data["incidents"] = incidents[(incidents["date"].dt.date >= period[0])
                                          & (incidents["date"].dt.date <= period[1])]

    topics = list(dict.fromkeys(q[0] for q in questions))
    topic = st.selectbox("Topic", topics)
    options = [q for q in questions if q[0] == topic]
    question = st.selectbox("Question", [q[1] for q in options])
    function = next(q[3] for q in options if q[1] == question)

    headline, table, chart = function(data)
    st.markdown(f"**{headline}**")
    if table is not None and not table.empty:
        left, right = st.columns([1, 2]) if chart else (st.container(), None)
        left.dataframe(table, hide_index=True)
        if chart:
            fig = px.bar(table, x=chart[0], y=chart[1], text=chart[1], color_discrete_sequence=[BLUE])
            fig.update_layout(margin=dict(t=20))
            right.plotly_chart(fig)
    elif table is not None:
        st.info("There are no matching records.")


def _summary_tab(data: dict, role: str, user_number) -> None:
    st.subheader("Recommendations")
    for text in recommendations(data, role):
        st.write(text)
    report = summary_text(data, role, user_number)
    st.download_button("Download summary report (text)", report, "khwezi_monitoring_report.txt", "text/plain")
    with st.expander("Preview the report"):
        st.code(report, language=None)


def show_reports() -> None:
    ensure_sample_data()
    role = st.session_state.get("role")
    workers, incidents, equipment = load_workers(), load_incidents(), load_equipment()
    data = {"workers": workers, "incidents": incidents, "equipment": equipment,
            "alerts": generate_alerts(workers, incidents, equipment, role)}

    page_header("Reports, Alerts and Analysis")
    st.caption("You only see the data your role is permitted to access. Limits are educational prototype "
               "thresholds, not mine safety limits.")
    alerts, analysis, summary = st.tabs(["Alerts", "Analysis questions", "Summary report"])
    with alerts:
        _alerts_tab(data["alerts"])
    with analysis:
        _analysis_tab(data, role)
    with summary:
        _summary_tab(data, role, st.session_state.get("user_number"))
