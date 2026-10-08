import ast

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# ---------------------------------------------------------
# Allowed Python syntax
# ---------------------------------------------------------

ALLOWED_NODES = {
    ast.Module,
    ast.Assign,
    ast.Expr,
    ast.Name,
    ast.Load,
    ast.Store,
    ast.Constant,
    ast.Subscript,
    ast.Attribute,
    ast.Call,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.IfExp,
    ast.List,
    ast.Tuple,
    ast.Dict,
    ast.Set,
    ast.Slice,
    ast.Index,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.And,
    ast.Or,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.BitAnd,
    ast.BitOr,
}


# ---------------------------------------------------------
# Allowed objects
# ---------------------------------------------------------

ALLOWED_NAMES = {
    "df",
    "pd",
    "px",
    "go",
    "result",
    "fig",
    "len",
    "int",
    "float",
    "str",
    "round",
}


BLOCKED_ATTRIBUTES = {
    "__class__",
    "__bases__",
    "__subclasses__",
    "__globals__",
    "__builtins__",
    "__dict__",
    "__code__",
    "__import__",
}


# ---------------------------------------------------------
# Validate generated code
# ---------------------------------------------------------

def validate_code(code):
    """
    Check generated Python code before execution.
    """

    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as error:
        return False, f"Syntax error: {error}"

    for node in ast.walk(tree):

        if type(node) not in ALLOWED_NODES:
            return False, (
                f"Blocked Python operation: "
                f"{type(node).__name__}"
            )

        if isinstance(node, ast.Name):

            if node.id not in ALLOWED_NAMES:
                return False, (
                    f"Blocked name: {node.id}"
                )

        if isinstance(node, ast.Attribute):

            if node.attr in BLOCKED_ATTRIBUTES:
                return False, (
                    f"Blocked attribute: {node.attr}"
                )

        if isinstance(node, ast.Call):

            if isinstance(node.func, ast.Name):
                if node.func.id not in ALLOWED_NAMES:
                    return False, (
                        f"Blocked function: {node.func.id}"
                    )

    return True, ""


# ---------------------------------------------------------
# Execute analysis
# ---------------------------------------------------------

def execute_analysis(code, df):
    """
    Validate and execute generated analysis code.

    Returns:
        result
        fig
    """

    is_valid, error = validate_code(code)

    if not is_valid:
        raise ValueError(
            f"Generated code failed safety validation: {error}"
        )


    # Give generated code access only to approved objects.
    safe_globals = {
    "__builtins__": {},
    "pd": pd,
    "px": px,
    "go": go,
    "len": len,
    "int": int,
    "float": float,
    "str": str,
    "round": round,
    }

    safe_locals = {
        "df": df.copy(),
        "result": None,
        "fig": None,
    }


    exec(
        code,
        safe_globals,
        safe_locals,
    )


    result = safe_locals.get("result")
    fig = safe_locals.get("fig")


    return result, fig