
PERMISSIONS = {
    "View dashboard":      {"Administrator", "Safety Officer", "Mining Engineer", "Maintenance Engineer", "Manager"},
    "Worker safety data":  {"Administrator", "Safety Officer", "Mining Engineer", "Manager"},
    "Safety incidents":    {"Administrator", "Safety Officer", "Mining Engineer", "Manager"},
    "Equipment data":      {"Administrator", "Mining Engineer", "Maintenance Engineer", "Manager"},
    "Maintenance data":    {"Administrator", "Mining Engineer", "Maintenance Engineer", "Manager"},
    "Risk assessment":     {"Administrator", "Safety Officer", "Mining Engineer", "Manager"},
    "Generate reports":    {"Administrator", "Safety Officer", "Mining Engineer", "Maintenance Engineer", "Manager"},
    "Manage users":        {"Administrator"},
}

ROLES = ["Administrator", "Safety Officer", "Mining Engineer", "Maintenance Engineer", "Manager"]


def has_permission(role: str, function: str) -> bool:
    """Return True if the given role may use the given function."""
    return role in PERMISSIONS.get(function, set())


def allowed_functions(role: str) -> list[str]:
    """Return the functions a role may see, in Table 1 order."""
    return [f for f, roles in PERMISSIONS.items() if role in roles]
