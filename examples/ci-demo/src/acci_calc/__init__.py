"""Tiny calculator used to validate the ACCI build/test pipeline."""
__version__ = "0.2.0"

OPS = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b,
    "%": lambda a, b: a % b,
}


def calc(a: float, op: str, b: float) -> float:
    if op not in OPS:
        raise ValueError(f"unknown operator {op!r}")
    if op in ("/", "%") and b == 0:
        raise ZeroDivisionError("division by zero")
    return OPS[op](a, b)


def fmt(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else repr(x)
