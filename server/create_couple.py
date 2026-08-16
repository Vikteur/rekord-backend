"""Create a wedding couple from the command line and print its magic links.

The quick way to set up "koppel X & Y, 25 May" without opening the app —

    python -m server.create_couple "Sofie & Jan" 2026-05-25 --dj sarah

In production (the image only ships `server/`):

    docker compose exec app python -m server.create_couple "Sofie & Jan" 2026-05-25

The couple belongs to `--dj`, or to the admin when omitted. Set
PUBLIC_BASE_URL (e.g. https://rekord.example.com) to print full links
instead of bare /g/<token> paths.
"""

import argparse
import os
import sys

from server import auth, couples, db


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m server.create_couple",
        description="Create a couple and print the two magic links to hand out.",
    )
    parser.add_argument("names", help='e.g. "Sofie & Jan"')
    parser.add_argument("wedding_date", help="e.g. 2026-05-25")
    parser.add_argument(
        "--dj", help="username of the DJ this wedding belongs to (default: the admin)"
    )
    args = parser.parse_args(argv)

    db.init()
    auth.init()
    couples.init()

    if args.dj:
        row = auth.find_by_username(args.dj)
        if row is None:
            print(f"No account named {args.dj!r}.", file=sys.stderr)
            return 1
        dj_id = row["id"]
    else:
        admins = [user for user in auth.list_users() if user["role"] == "admin"]
        if not admins:
            print(
                "No admin account exists yet — create one first"
                " (python -m server.create_user <name> --role admin).",
                file=sys.stderr,
            )
            return 1
        dj_id = admins[0]["id"]

    try:
        couple_id = couples.create_couple(args.names, args.wedding_date, dj_id=dj_id)
    except couples.CoupleError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    couple = couples.get_couple(couple_id)
    base = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    print(f"Created couple #{couple_id}: {couple['names']} ({couple['wedding_date']})")
    print(f"  Couple link:  {base}/g/{couple['couple_token']}")
    print(f"  Friends link: {base}/g/{couple['friends_token']}")
    print("Both links stop working the day after the wedding.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
