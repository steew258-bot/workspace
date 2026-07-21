import argparse
import json

from src.modules.triage import triage


def main(argv=None):
    parser = argparse.ArgumentParser(prog="ops-agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    triage_parser = subparsers.add_parser("triage", help="Analyse un texte et propose une action")
    triage_parser.add_argument("text", help="Texte a trier (email, tache, notification...)")

    args = parser.parse_args(argv)

    if args.command == "triage":
        result = triage(args.text)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
