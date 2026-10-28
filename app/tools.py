"""A limited arithmetic tool for the single agent. No Python eval/exec."""

import ast
import math
import operator

OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def calculate_expression(expression: str) -> str:
    """Evaluate basic arithmetic only, with size/depth limits."""
    if not expression or len(expression) > 100:
        raise ValueError("Expression must contain 1-100 characters")
    try:
        node = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError("Invalid arithmetic expression") from exc

    def walk(current: ast.AST, depth: int = 0) -> float | int:
        if depth > 15:
            raise ValueError("Expression too complex")
        if isinstance(current, ast.Expression):
            return walk(current.body, depth + 1)
        if isinstance(current, ast.Constant) and type(current.value) in (float, int):
            value = current.value
            if not math.isfinite(value) or abs(value) > 1e10:
                raise ValueError("Number is too large")
            return value
        if isinstance(current, ast.UnaryOp) and type(current.op) in (ast.UAdd, ast.USub):
            return OPERATORS[type(current.op)](walk(current.operand, depth + 1))
        if isinstance(current, ast.BinOp) and type(current.op) in OPERATORS:
            left = walk(current.left, depth + 1)
            right = walk(current.right, depth + 1)
            if isinstance(current.op, ast.Pow) and (abs(left) > 1e6 or abs(right) > 12):
                raise ValueError("Exponentiation limit exceeded")
            try:
                output = OPERATORS[type(current.op)](left, right)
            except (OverflowError, ZeroDivisionError) as exc:
                raise ValueError("Invalid arithmetic operation") from exc
            if not math.isfinite(output) or abs(output) > 1e12:
                raise ValueError("Result too large")
            return output
        raise ValueError("Only numeric arithmetic (+, -, *, /, //, %, **) is allowed")

    result = walk(node)
    return str(result)
