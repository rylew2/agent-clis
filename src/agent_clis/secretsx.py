"""Manage agent-clis secrets in the OS credential store (Windows Credential Manager).

Secrets are stored via the `keyring` library under service=agent-clis, with each
variable name as the username. This CLI sets, lists, deletes, imports, and diagnoses
those entries. It never prints secret values.
"""

from __future__ import annotations

import argparse
import getpass
from pathlib import Path

from .common import (
    AgentCliError,
    KEYRING_SERVICE,
    SECRET_NAMES,
    _candidate_env_files,
    main_wrapper,
)

# Non-secret config lines that legitimately stay in .env; used by `import --purge`
# to decide what to keep.
NON_SECRET_KEYS = {
    "REDDIT_USER_AGENT",
    "ATLASSIAN_BASE_URL",
    "ATLASSIAN_EMAIL",
    "GOOGLE_APPLICATION_CREDENTIALS",
}


def _keyring():
    try:
        import keyring
    except Exception as exc:  # noqa: BLE001
        raise AgentCliError(
            "The 'keyring' package is required. Install it with: pip install keyring"
        ) from exc
    return keyring


def _store_get(name: str) -> str | None:
    try:
        return _keyring().get_password(KEYRING_SERVICE, name) or None
    except Exception:  # noqa: BLE001
        return None


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and value:
            values[key] = value
    return values


def _default_env_path() -> Path:
    for path in _candidate_env_files():
        if path.is_file():
            return path
    raise AgentCliError("No .env file found to import from. Pass --env PATH.")


def cmd_set(args: argparse.Namespace) -> int:
    name = args.name
    value = args.value or getpass.getpass(f"Value for {name} (input hidden): ")
    if not value:
        raise AgentCliError("Empty value; nothing stored.")
    _keyring().set_password(KEYRING_SERVICE, name, value)
    print(f"Stored {name} in credential store (service={KEYRING_SERVICE}).")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    print(f"Secrets in credential store (service={KEYRING_SERVICE}):")
    for name in SECRET_NAMES:
        state = "set" if _store_get(name) else "-"
        print(f"  {name:<24} {state}")
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    try:
        _keyring().delete_password(KEYRING_SERVICE, args.name)
    except Exception as exc:  # noqa: BLE001 - includes "not found".
        raise AgentCliError(f"Could not delete {args.name}: {exc}") from exc
    print(f"Deleted {args.name} from credential store.")
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    env_path = Path(args.env) if args.env else _default_env_path()
    values = _parse_env_file(env_path)
    imported: list[str] = []
    skipped_empty: list[str] = []
    for name in SECRET_NAMES:
        value = values.get(name)
        if not value:
            skipped_empty.append(name)
            continue
        _keyring().set_password(KEYRING_SERVICE, name, value)
        imported.append(name)

    print(f"Imported {len(imported)} secret(s) from {env_path} into credential store:")
    for name in imported:
        print(f"  + {name}")
    if skipped_empty:
        print(f"Not present/empty in {env_path.name}: {', '.join(skipped_empty)}")

    if args.purge:
        _purge_env(env_path)
    else:
        print("\nRun again with --purge to remove the secret values from the .env file.")
    return 0


def _purge_env(env_path: Path) -> None:
    kept: list[str] = []
    removed: list[str] = []
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in SECRET_NAMES:
                # Leave an empty placeholder. The note goes on its own comment line
                # so the .env parser never reads it as the value (inline comments are
                # not stripped by _load_dotenv_once).
                kept.append(f"# {key} moved to credential store; run: secretsx set {key}")
                kept.append(f"{key}=")
                removed.append(key)
                continue
        kept.append(raw_line)
    env_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
    print(f"\nPurged {len(removed)} secret value(s) from {env_path}: {', '.join(removed) or 'none'}")


def cmd_doctor(args: argparse.Namespace) -> int:
    import os

    kr = _keyring()
    print(f"keyring backend: {kr.get_keyring()}")
    print(f"service: {KEYRING_SERVICE}\n")
    print(f"{'SECRET':<24} {'RESOLVES FROM':<14}")
    for name in SECRET_NAMES:
        if os.getenv(name):
            source = "env"
        elif _store_get(name):
            source = "store"
        else:
            source = "missing"
        print(f"{name:<24} {source:<14}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="secretsx",
        description="Manage agent-clis secrets in the OS credential store (Windows Credential Manager).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    set_cmd = sub.add_parser("set", help="Store a secret (hidden prompt unless --value given).")
    set_cmd.add_argument("name", help="Variable name, e.g. EXA_API_KEY.")
    set_cmd.add_argument("--value", help="Value (omit to be prompted with hidden input).")
    set_cmd.set_defaults(func=cmd_set)

    list_cmd = sub.add_parser("list", help="List known secret names and whether each is set.")
    list_cmd.set_defaults(func=cmd_list)

    del_cmd = sub.add_parser("delete", help="Remove a secret from the store.")
    del_cmd.add_argument("name")
    del_cmd.set_defaults(func=cmd_delete)

    import_cmd = sub.add_parser("import", help="Import secrets from a .env file into the store.")
    import_cmd.add_argument("--env", help="Path to .env (default: first discovered .env).")
    import_cmd.add_argument(
        "--purge", action="store_true", help="Also strip secret values from the .env file."
    )
    import_cmd.set_defaults(func=cmd_import)

    doctor = sub.add_parser("doctor", help="Show backend and where each secret resolves from.")
    doctor.set_defaults(func=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    def run() -> int:
        args = build_parser().parse_args(argv)
        return args.func(args)

    return main_wrapper(run)


if __name__ == "__main__":
    raise SystemExit(main())
