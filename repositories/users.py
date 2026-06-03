from infra.db import execute, get_conn


def upsert_user(user_id: int, username: str, full_name: str) -> None:
    execute(
        """
        INSERT INTO users (id, username, full_name) VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            username  = excluded.username,
            full_name = excluded.full_name
        """,
        (user_id, username, full_name),
    )
    execute(
        "INSERT OR IGNORE INTO wallet_balances (user_id, balance_usd) VALUES (?, 0)",
        (user_id,),
    )
    get_conn().commit()


def get_user_language(user_id: int) -> str:
    row = execute("SELECT language FROM users WHERE id = ?", (user_id,)).fetchone()
    return row[0] if row else "ar"


def set_user_language(user_id: int, language: str) -> None:
    execute("UPDATE users SET language = ? WHERE id = ?", (language, user_id))
    get_conn().commit()


def get_all_users() -> list:
    return execute(
        "SELECT id, username, full_name FROM users WHERE blocked = 0"
    ).fetchall()
