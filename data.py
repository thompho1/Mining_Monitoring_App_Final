
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from monitoring import availability, classify_risk, equipment_status

DATA_DIR = Path(__file__).parent / "data"
WORKERS_CSV = DATA_DIR / "workers.csv"
INCIDENTS_CSV = DATA_DIR / "incidents.csv"
EQUIPMENT_CSV = DATA_DIR / "equipment.csv"

DEPARTMENTS = ["Underground Mining", "Surface Mining", "Processing Plant",
               "Maintenance Workshop", "Engineering"]
LOCATIONS = {
    "Underground Mining": ["Level 12 Stope", "Level 14 Haulage", "Shaft Station 3"],
    "Surface Mining": ["Pit North", "Pit South", "Waste Dump"],
    "Processing Plant": ["Crusher Station", "Milling Circuit", "Stockpile"],
    "Maintenance Workshop": ["Main Workshop", "Tyre Bay"],
    "Engineering": ["Survey Office", "Control Room"],
}
JOB_ROLES = ["Miner", "Driller", "Equipment Operator", "Artisan", "Supervisor", "Engineer"]

INCIDENT_TYPES = ["Near Miss", "First Aid", "Medical Treatment", "Property Damage",
                  "Fall of Ground", "Equipment Failure", "Slip/Trip/Fall"]
INJURY_TYPES = {"First Aid", "Medical Treatment", "Fall of Ground", "Slip/Trip/Fall"}
CAUSES = ["Unsafe act", "Unsafe condition", "Equipment failure", "Poor housekeeping",
          "Inadequate supervision", "Fatigue", "Inadequate training"]
ACTIONS = ["Retraining", "Equipment repair", "Area barricaded", "Procedure reviewed",
           "Additional supervision", "Housekeeping improved"]

EQUIPMENT_TYPES = {
    "Haul Truck": ("TRK", ["Caterpillar", "Komatsu", "Hitachi"]),
    "Loader": ("LDR", ["Caterpillar", "Sandvik", "Epiroc"]),
    "Excavator": ("EXC", ["Komatsu", "Hitachi", "Liebherr"]),
    "Drilling Machine": ("DRL", ["Epiroc", "Sandvik"]),
    "Bulldozer": ("BLD", ["Caterpillar", "Komatsu"]),
    "Scraper Winch": ("SCW", ["Joy Global", "Sandvik"]),
    "Crusher": ("CRH", ["Metso", "FLSmidth"]),
    "Conveyor": ("CNV", ["Continental", "Bonfiglioli"]),
}
FIXED_PLANT = {"Crusher", "Conveyor", "Scraper Winch"}


def _build_workers(rng: random.Random) -> pd.DataFrame:
    rows = []
    for i in range(1, 61):
        rows.append({
            "worker_id": f"W{i:03d}",
            "department": rng.choice(DEPARTMENTS),
            "job_role": rng.choice(JOB_ROLES),
            "shift": rng.choice(["Day", "Night"]),
            "ppe_compliant": "Yes" if rng.random() < 0.85 else "No",
            "training_status": "Valid" if rng.random() < 0.88 else "Expired",
            "fatigue_level": rng.randint(1, 10),
            "safety_observations": rng.randint(0, 6),
            "near_misses": rng.randint(0, 3),
            "previous_incidents": rng.choices([0, 1, 2, 3], weights=[60, 25, 10, 5])[0],
            "likelihood": rng.randint(1, 5),
            "consequence": rng.randint(1, 5),
        })
    return pd.DataFrame(rows)


def _build_incidents(rng: random.Random) -> pd.DataFrame:
    today = date.today()
    rows = []
    for i in range(1, 81):
        department = rng.choice(DEPARTMENTS)
        hour = rng.randint(0, 23)
        incident_type = rng.choices(INCIDENT_TYPES, weights=[25, 18, 8, 12, 6, 14, 17])[0]
        if incident_type == "Near Miss":
            severity = rng.choice(["Low", "Medium"])
        else:
            severity = rng.choices(["Low", "Medium", "High", "Critical"], weights=[35, 35, 20, 10])[0]
        injury = incident_type in INJURY_TYPES and rng.random() < 0.8
        lost_time = injury and severity in ("High", "Critical") and rng.random() < 0.7
        rows.append({
            "incident_id": f"INC-{i:04d}",
            "date": (today - timedelta(days=rng.randint(0, 180))).isoformat(),
            "time": f"{hour:02d}:{rng.choice([0, 15, 30, 45]):02d}",
            "shift": "Day" if 6 <= hour < 18 else "Night",
            "location": rng.choice(LOCATIONS[department]),
            "department": department,
            "incident_type": incident_type,
            "severity": severity,
            "injury": "Yes" if injury else "No",
            "lost_time_injury": "Yes" if lost_time else "No",
            "cause": rng.choice(CAUSES),
            "corrective_action": rng.choice(ACTIONS),
            "status": rng.choices(["Open", "Under Investigation", "Closed"], weights=[25, 25, 50])[0],
        })
    return pd.DataFrame(rows)


def _build_equipment(rng: random.Random) -> pd.DataFrame:
    rows = []
    for eq_type, (prefix, makers) in EQUIPMENT_TYPES.items():
        for n in range(1, 4):
            fixed = eq_type in FIXED_PLANT
            rows.append({
                "equipment_id": f"{prefix}-{n:03d}",
                "equipment_type": eq_type,
                "manufacturer": rng.choice(makers),
                "operating_hours": rng.randint(300, 700),
                "downtime_hours": rng.randint(5, 120),
                "temperature": round(min(max(rng.gauss(78, 14), 50), 115), 1),
                "vibration": round(min(max(rng.gauss(4.5, 2.2), 1), 11), 1),
                "fuel_consumption": 0 if fixed else rng.randint(20, 90),
                "brake_status": "N/A" if fixed else rng.choices(["OK", "Worn", "Faulty"], weights=[70, 22, 8])[0],
                "tyre_status": "N/A" if fixed else rng.choices(["OK", "Worn", "Replace"], weights=[65, 25, 10])[0],
                "engine_status": rng.choices(["Normal", "Fault"], weights=[90, 10])[0],
                "maintenance_status": rng.choices(
                    ["Operational", "Due", "Overdue", "Under Maintenance"], weights=[60, 15, 10, 15])[0],
                "alert_count": rng.randint(0, 8),
            })
    return pd.DataFrame(rows)


def ensure_sample_data() -> None:
    """Create the sample CSV files if any of them is missing."""
    if WORKERS_CSV.exists() and INCIDENTS_CSV.exists() and EQUIPMENT_CSV.exists():
        return
    DATA_DIR.mkdir(exist_ok=True)
    rng = random.Random(42)
    _build_workers(rng).to_csv(WORKERS_CSV, index=False)
    _build_incidents(rng).to_csv(INCIDENTS_CSV, index=False)
    _build_equipment(rng).to_csv(EQUIPMENT_CSV, index=False)


def load_workers() -> pd.DataFrame:
    df = pd.read_csv(WORKERS_CSV)
    risk = [classify_risk(l, c) for l, c in zip(df["likelihood"], df["consequence"])]
    df["risk_score"] = [score for score, _ in risk]
    df["risk_level"] = [level for _, level in risk]
    return df


WORKER_COLUMNS = ["worker_id", "department", "job_role", "shift", "ppe_compliant",
                  "training_status", "fatigue_level", "safety_observations", "near_misses",
                  "previous_incidents", "likelihood", "consequence"]


def next_worker_id(workers: pd.DataFrame) -> str:

    numbers = pd.to_numeric(workers["worker_id"].str.extract(r"(\d+)$")[0], errors="coerce")
    return f"W{int(numbers.max() if len(numbers) else 0) + 1:03d}"


def append_worker(record: dict) -> None:
    """Add one worker record to workers.csv."""
    df = pd.read_csv(WORKERS_CSV)
    df = pd.concat([df, pd.DataFrame([record], columns=WORKER_COLUMNS)], ignore_index=True)
    df.to_csv(WORKERS_CSV, index=False)


def load_incidents() -> pd.DataFrame:
    df = pd.read_csv(INCIDENTS_CSV)
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_equipment() -> pd.DataFrame:
    df = pd.read_csv(EQUIPMENT_CSV)
    df["availability"] = [availability(o, d) for o, d in zip(df["operating_hours"], df["downtime_hours"])]
    df["condition"] = [equipment_status(t, v) for t, v in zip(df["temperature"], df["vibration"])]
    return df


INCIDENT_COLUMNS = ["incident_id", "date", "time", "shift", "location", "department", "incident_type",
                    "severity", "injury", "lost_time_injury", "cause", "corrective_action", "status"]
EQUIPMENT_COLUMNS = ["equipment_id", "equipment_type", "manufacturer", "operating_hours",
                     "downtime_hours", "temperature", "vibration", "fuel_consumption", "brake_status",
                     "tyre_status", "engine_status", "maintenance_status", "alert_count"]


def next_incident_id(incidents: pd.DataFrame) -> str:

    numbers = pd.to_numeric(incidents["incident_id"].str.extract(r"(\d+)$")[0], errors="coerce")
    return f"INC-{int(numbers.max() if len(numbers) else 0) + 1:04d}"


def append_incident(record: dict) -> None:
    """Add one incident to incidents.csv. The date must be an ISO string."""
    df = pd.read_csv(INCIDENTS_CSV)
    df = pd.concat([df, pd.DataFrame([record], columns=INCIDENT_COLUMNS)], ignore_index=True)
    df.to_csv(INCIDENTS_CSV, index=False)


def append_equipment(record: dict) -> None:
    """Add one piece of equipment to equipment.csv."""
    df = pd.read_csv(EQUIPMENT_CSV)
    df = pd.concat([df, pd.DataFrame([record], columns=EQUIPMENT_COLUMNS)], ignore_index=True)
    df.to_csv(EQUIPMENT_CSV, index=False)


def update_equipment(equipment_id: str, changes: dict) -> None:
    """Change fields of one equipment record in equipment.csv."""
    df = pd.read_csv(EQUIPMENT_CSV)
    rows = df.index[df["equipment_id"] == equipment_id]
    if len(rows) == 0:
        raise KeyError(f"Equipment {equipment_id} not found")
    for column, value in changes.items():
        df.loc[rows, column] = value
    df.to_csv(EQUIPMENT_CSV, index=False)


def update_worker_risk(worker_id: str, likelihood: int, consequence: int) -> None:
    """Store a new likelihood and consequence for one worker."""
    df = pd.read_csv(WORKERS_CSV)
    rows = df.index[df["worker_id"] == worker_id]
    if len(rows) == 0:
        raise KeyError(f"Worker {worker_id} not found")
    df.loc[rows, "likelihood"] = int(likelihood)
    df.loc[rows, "consequence"] = int(consequence)
    df.to_csv(WORKERS_CSV, index=False)
