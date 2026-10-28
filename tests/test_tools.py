import pytest

from app.tools import calculate_expression


@pytest.mark.parametrize("expression,expected", [
    ("2 + 3 * 4", "14"),
    ("(20 - 5) / 3", "5.0"),
    ("-2 ** 3", "-8"),
    ("450000 * 1.5", "675000.0"),
])
def test_calculator(expression, expected):
    assert calculate_expression(expression) == expected


@pytest.mark.parametrize("expression", [
    "__import__('os').system('id')",
    "1 / 0",
    "2 ** 10000",
    "[1,2,3]",
    "4 + example",
])
def test_calculator_rejects_invalid(expression):
    with pytest.raises(ValueError):
        calculate_expression(expression)
