from werkzeug.security import generate_password_hash


def main() -> None:
    raw = input("Enter dashboard password: ").strip()
    if not raw:
        print("Password cannot be empty")
        return
    print(generate_password_hash(raw))


if __name__ == "__main__":
    main()
