from infra.db import execute


def log_action(
    actor: str,
    action: str,
    target_type: str,
    target_id: str,
    details: str = "",
) -> None:
    execute(
        "INSERT INTO admin_audit_logs (actor, action, target_type, target_id, details) VALUES (?, ?, ?, ?, ?)",
        (actor, action, target_type, target_id, details),
    )
