
TEMP_WARNING = 80      # degrees C
TEMP_CRITICAL = 100
VIB_WARNING = 5        # mm/s
VIB_CRITICAL = 8

_SEVERITY_RANK = {"NORMAL": 0, "WARNING": 1, "CRITICAL": 2}


def classify_temperature(temperature: float) -> str:
    if temperature > TEMP_CRITICAL:
        return "CRITICAL"
    if temperature >= TEMP_WARNING:
        return "WARNING"
    return "NORMAL"


def classify_vibration(vibration: float) -> str:
    if vibration > VIB_CRITICAL:
        return "CRITICAL"
    if vibration >= VIB_WARNING:
        return "WARNING"
    return "NORMAL"


def equipment_status(temperature: float, vibration: float) -> str:
    """Overall condition is the worst of the temperature and vibration results."""
    temp_status = classify_temperature(temperature)
    vib_status = classify_vibration(vibration)
    return max(temp_status, vib_status, key=_SEVERITY_RANK.get)


def availability(operating_time: float, downtime: float) -> float:
    """Availability = operating time / (operating time + downtime) x 100."""
    total = operating_time + downtime
    if total == 0:
        return 0.0
    return operating_time / total * 100


def classify_risk(likelihood: int, consequence: int) -> tuple[int, str]:
    """RiskScore = Likelihood x Consequence on a 1-5 scale."""
    score = likelihood * consequence
    if score >= 17:
        level = "Critical"
    elif score >= 10:
        level = "High"
    elif score >= 5:
        level = "Medium"
    else:
        level = "Low"
    return score, level



FATIGUE_WARNING = 7
NEAR_MISS_WARNING = 2
PREVIOUS_INCIDENT_WARNING = 2


def worker_warnings(worker) -> list[str]:

    warnings = []
    if worker["ppe_compliant"] != "Yes":
        warnings.append("PPE non-compliance")
    if worker["training_status"] != "Valid":
        warnings.append("Safety training expired")
    if worker["fatigue_level"] >= FATIGUE_WARNING:
        warnings.append("High fatigue level")
    if worker["near_misses"] >= NEAR_MISS_WARNING:
        warnings.append("Repeated near misses")
    if worker["previous_incidents"] >= PREVIOUS_INCIDENT_WARNING:
        warnings.append("Repeated previous incidents")
    if worker["risk_level"] in ("High", "Critical"):
        warnings.append(f"{worker['risk_level']} risk level")
    return warnings



EXCESSIVE_DOWNTIME_HOURS = 100
REPEATED_ALERT_COUNT = 5
LOW_AVAILABILITY = 85.0       # percent
PPE_COMPLIANCE_MIN = 80.0     # percent, per department
FATIGUE_ALERT = 9             # fatigue level on a 1-10 scale


def condition_message(temperature: float, vibration: float) -> tuple[str, str]:
    """Return (status, message) in the wording used by the brief."""
    temp = classify_temperature(temperature)
    vib = classify_vibration(vibration)
    status = equipment_status(temperature, vibration)
    if status == "NORMAL":
        return status, "Equipment operating within defined monitoring limits."
    if status == "CRITICAL":
        parts = []
        if vib == "CRITICAL":
            parts.append("Equipment vibration exceeds predefined threshold.")
        if temp == "CRITICAL":
            parts.append("Equipment temperature exceeds predefined threshold.")
        return status, " ".join(parts) + " Inspection required"
    parts = []
    if temp == "WARNING":
        parts.append("Equipment temperature approaching predefined threshold.")
    if vib == "WARNING":
        parts.append("Equipment vibration approaching predefined threshold.")
    return status, " ".join(parts)


def maintenance_flags(equipment) -> list[str]:
    """Return the maintenance categories (section f) that apply to one equipment row."""
    flags = []
    if equipment["maintenance_status"] == "Due":
        flags.append("Due for maintenance")
    if equipment["maintenance_status"] == "Overdue":
        flags.append("Overdue")
    if equipment["maintenance_status"] == "Under Maintenance":
        flags.append("Under maintenance")
    if equipment["downtime_hours"] > EXCESSIVE_DOWNTIME_HOURS:
        flags.append("Excessive downtime")
    if equipment["alert_count"] >= REPEATED_ALERT_COUNT:
        flags.append("Repeated alerts")
    if equipment["availability"] < LOW_AVAILABILITY:
        flags.append("Low availability")
    return flags


def maintenance_priority(equipment) -> int:
    """A simple priority score: the higher the number, the sooner it needs attention."""
    score = {"CRITICAL": 3, "WARNING": 1}.get(equipment["condition"], 0)
    score += {"Overdue": 3, "Due": 1}.get(equipment["maintenance_status"], 0)
    if equipment["downtime_hours"] > EXCESSIVE_DOWNTIME_HOURS:
        score += 1
    if equipment["alert_count"] >= REPEATED_ALERT_COUNT:
        score += 1
    if equipment["availability"] < LOW_AVAILABILITY:
        score += 1
    return score
