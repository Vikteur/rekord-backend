"""Create or reset a DJ-app account from the command line.

Lives under `server/` on purpose: it's the only code that ships in the
Docker image, so this also works in production —

    docker compose exec app python -m server.create_user sarah
    docker compose exec app python -m server.create_user viktor --reset

Without `--password` the password is prompted for without echo.
"""

import argparse
import getpass
import sys

from server import auth, couples, db


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m server.create_user",
        description="Create a DJ-app account, or reset an existing password.",
    )
    parser.add_argument("username", help="sign-in name, e.g. sarah")
    parser.add_argument(
        "--display-name", default="", help='shown in the app, e.g. "Sarah V."'
    )
    parser.add_argument(
        "--role", choices=("dj", "admin"), default="dj",
        help="dj (default) or admin",
    )
    parser.add_argument(
        "--password", help="omit to be prompted for it without echo"
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="set a new password for an existing account instead of creating one",
    )
    args = parser.parse_args(argv)

    # Safe on an existing database; creates the tables on a fresh one.
    db.init()
    auth.init()
    couples.init()

    password = args.password or getpass.getpass(
        f"New password for {args.username} (min {auth.MIN_PASSWORD_CHARS} chars): "
    )
    try:
        if args.reset:
            row = auth.find_by_username(args.username)
            if row is None:
                print(f"No account named {args.username!r}.", file=sys.stderr)
                return 1
            auth.set_password(row["id"], password)
            print(f"Password reset for {args.username}.")
        else:
            auth.create_user(args.username, args.display_name, password, args.role)
            print(f"Created {args.role} account {args.username!r}. They can sign in now.")
    except auth.AuthError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
