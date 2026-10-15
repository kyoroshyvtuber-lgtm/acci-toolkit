import argparse
import sys

from acci_calc import OPS, __version__, calc, fmt


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="acci-calc", description="a OP b calculator")
    p.add_argument("--version", action="version", version=f"acci-calc {__version__}")
    p.add_argument("a", type=float)
    p.add_argument("op", choices=list(OPS))
    p.add_argument("b", type=float)
    args = p.parse_args(argv)
    try:
        print(fmt(calc(args.a, args.op, args.b)))
    except ZeroDivisionError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


def run() -> None:
    """Entry point for zipapp/console use: propagate main()'s exit code."""
    sys.exit(main())


if __name__ == "__main__":
    run()
