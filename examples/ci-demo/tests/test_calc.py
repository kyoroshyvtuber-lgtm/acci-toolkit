import pytest

from acci_calc import calc, fmt
from acci_calc.__main__ import main, run


@pytest.mark.parametrize("a,op,b,expected", [(2, "+", 3, 5), (5, "-", 7, -2), (6, "*", 7, 42), (7, "/", 2, 3.5)])
def test_calc(a, op, b, expected):
    assert calc(a, op, b) == expected


def test_division_by_zero():
    with pytest.raises(ZeroDivisionError):
        calc(1, "/", 0)


def test_unknown_operator():
    with pytest.raises(ValueError):
        calc(1, "^", 2)


def test_fmt():
    assert fmt(42.0) == "42" and fmt(3.5) == "3.5"


def test_cli(capsys):
    assert main(["6", "*", "7"]) == 0
    assert capsys.readouterr().out.strip() == "42"


@pytest.mark.parametrize("a,b,expected", [(7, 3, 1), (-7, 3, 2), (7.5, 2, 1.5)])
def test_modulo(a, b, expected):
    assert calc(a, "%", b) == expected


def test_modulo_by_zero():
    with pytest.raises(ZeroDivisionError):
        calc(1, "%", 0)


def test_cli_modulo_and_zero(capsys):
    assert main(["7", "%", "3"]) == 0
    assert capsys.readouterr().out.strip() == "1"
    assert main(["1", "%", "0"]) == 2
    assert "division by zero" in capsys.readouterr().err


def test_run_propagates_exit_code(monkeypatch):
    monkeypatch.setattr("sys.argv", ["acci-calc", "1", "%", "0"])
    with pytest.raises(SystemExit) as e:
        run()
    assert e.value.code == 2
