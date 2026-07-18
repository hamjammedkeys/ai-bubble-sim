import argparse

from fragility_map.ingestion.refresh import refresh_sources


def main() -> None:
    parser = argparse.ArgumentParser(prog="fragility-map")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("refresh")
    args = parser.parse_args()
    if args.command == "refresh":
        count = refresh_sources()
        print(f"Refreshed {count} companies")
