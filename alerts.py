
import textwrap

import pandas as pd

from monitoring import (
    EXCESSIVE_DOWNTIME_HOURS,
    FATIGUE_ALERT,
    PPE_COMPLIANCE_MIN,
    TEMP_CRITICAL,
    TEMP_WARNING,
    VIB_CRITICAL,
    VIB_WARNING,
    classify_temperature,
    classify_vibration,
)
from permissions import has_permission

BAR = "=" * 53
EQUIPMENT_CRITICAL_ACTION = "Inspect equipment and initiate appropriate maintenance/safety procedures."
EQUIPMENT_WARNING_ACTION = "Monitor equipment closely and schedule an inspection."


def _alert(severity, category, subject_label, subject, parameter, value, status, action) -> dict:
    return {"severity": severity, "category": category, "subject_label": subject_label,
            "subject": subject, "parameter": parameter, "value": value, "status": status,
            "action": action}


def _equipment_alerts(equipment: pd.DataFrame, role: str) -> list[dict]:
    alerts = []
    if has_permission(role, "Equipment data"):
        for _, e in equipment.iterrows():
            temp = classify_temperature(e["temperature"])
            if temp != "NORMAL":
                critical = temp == "CRITICAL"
                alerts.append(_alert(
                    temp, "High equipment temperature", "Equipment ID", e["equipment_id"],
                    "Temperature", f"{e['temperature']:.1f} °C",
                    f"Above Critical Threshold ({TEMP_CRITICAL} °C)" if critical
                    else f"In Warning Range ({TEMP_WARNING}-{TEMP_CRITICAL} °C)",
                    EQUIPMENT_CRITICAL_ACTION if critical else EQUIPMENT_WARNING_ACTION))
            vib = classify_vibration(e["vibration"])
            if vib != "NORMAL":
                critical = vib == "CRITICAL"
                alerts.append(_alert(
                    vib, "High equipment vibration", "Equipment ID", e["equipment_id"],
                    "Vibration", f"{e['vibration']:.1f} mm/s",
                    f"Above Critical Threshold ({VIB_CRITICAL} mm/s)" if critical
                    else f"In Warning Range ({VIB_WARNING}-{VIB_CRITICAL} mm/s)",
                    EQUIPMENT_CRITICAL_ACTION if critical else EQUIPMENT_WARNING_ACTION))
            if e["downtime_hours"] > EXCESSIVE_DOWNTIME_HOURS:
                alerts.append(_alert(
                    "WARNING", "Excessive equipment downtime", "Equipment ID", e["equipment_id"],
                    "Downtime", f"{int(e['downtime_hours'])} h",
                    f"Above Downtime Limit ({EXCESSIVE_DOWNTIME_HOURS} h)",
                    "Review the causes of downtime and plan corrective maintenance."))
    if has_permission(role, "Maintenance data"):
        for _, e in equipment[equipment["maintenance_status"] == "Overdue"].iterrows():
            alerts.append(_alert(
                "WARNING", "Overdue maintenance", "Equipment ID", e["equipment_id"],
                "Maintenance status", "Overdue", "Maintenance Overdue",
                "Schedule the overdue maintenance as soon as possible."))
    return alerts


def _worker_alerts(workers: pd.DataFrame, role: str) -> list[dict]:
    alerts = []
    if not has_permission(role, "Worker safety data"):
        return alerts
    for department, group in workers.groupby("department"):
        compliance = (group["ppe_compliant"] == "Yes").mean() * 100
        if compliance < PPE_COMPLIANCE_MIN:
            alerts.append(_alert(
                "WARNING", "Low PPE compliance", "Department", department,
                "PPE compliance", f"{compliance:.1f} %",
                f"Below Minimum ({PPE_COMPLIANCE_MIN:.0f} %)",
                "Review PPE issue and enforce PPE requirements before work continues."))
    for _, w in workers.iterrows():
        if w["fatigue_level"] >= FATIGUE_ALERT:
            alerts.append(_alert(
                "WARNING", "High fatigue level", "Worker ID", w["worker_id"],
                "Fatigue level", f"{int(w['fatigue_level'])} / 10",
                f"At or Above Alert Level ({FATIGUE_ALERT})",
                "Review the worker's shift and rest period; consider reassigning duties."))
        if w["risk_level"] in ("High", "Critical"):
            alerts.append(_alert(
                w["risk_level"].upper() if w["risk_level"] == "Critical" else "WARNING",
                "High-risk safety observation", "Worker ID", w["worker_id"],
                "Risk score", f"{int(w['risk_score'])} ({w['risk_level']})",
                f"{w['risk_level']} Risk Classification",
                "Review controls and implement risk reduction measures."))
    return alerts


def _incident_alerts(incidents: pd.DataFrame, role: str) -> list[dict]:
    alerts = []
    if not has_permission(role, "Safety incidents"):
        return alerts
    open_critical = incidents[(incidents["severity"] == "Critical") & (incidents["status"] != "Closed")]
    for _, i in open_critical.iterrows():
        alerts.append(_alert(
            "CRITICAL", "Critical safety incident", "Incident ID", i["incident_id"],
            "Severity", "Critical", f"Incident {i['status']} ({i['incident_type']})",
            "Complete the investigation and implement corrective actions urgently."))
    return alerts


def generate_alerts(workers: pd.DataFrame, incidents: pd.DataFrame,
                    equipment: pd.DataFrame, role: str) -> list[dict]:

    alerts = _equipment_alerts(equipment, role) + _worker_alerts(workers, role) \
        + _incident_alerts(incidents, role)
    order = {"CRITICAL": 0, "WARNING": 1}
    return sorted(alerts, key=lambda a: (order[a["severity"]], a["category"], a["subject"]))


def format_alert(alert: dict) -> str:

    action = textwrap.fill(alert["action"], width=46, initial_indent="    ", subsequent_indent="    ")
    lines = [
        BAR, "", "KHWEZI MINING MONITORING ALERT".center(len(BAR)).rstrip(), "", BAR, "",
        f"[{alert['severity']}]".center(len(BAR)).rstrip(), "",
        f"{alert['subject_label']}: {alert['subject']}", "",
        f"Parameter: {alert['parameter']}", "",
        f"Value: {alert['value']}", "",
        f"Status: {alert['status']}", "",
        "Recommended Action:", "", action, "", BAR,
    ]
    return "\n".join(lines)


def alerts_table(alerts: list[dict]) -> pd.DataFrame:
    columns = ["severity", "category", "subject_label", "subject", "parameter", "value", "status"]
    return pd.DataFrame(alerts, columns=columns)
