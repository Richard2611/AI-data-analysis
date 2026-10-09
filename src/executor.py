import ast
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# Names that the generated code is allowed to access directly.
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
    "True",
    "False",
    "None",
}


# Dangerous names that must never be accessible.
BLOCKED_NAMES = {
    "__import__",
    "__builtins__",
    "__globals__",
    "__locals__",
    "__code__",
    "__class__",
    "__bases__",
    "__subclasses__",
    "__mro__",
    "__getattribute__",
    "__setattr__",
    "__delattr__",
    "eval",
    "exec",
    "open",
    "compile",
    "globals",
    "locals",
    "vars",
    "getattr",
    "setattr",
    "delattr",
    "input",
    "help",
    "dir",
    "breakpoint",
    "memoryview",
}


# Dangerous attributes that should never be accessed.
BLOCKED_ATTRIBUTES = {
    "__class__",
    "__bases__",
    "__subclasses__",
    "__globals__",
    "__locals__",
    "__code__",
    "__builtins__",
    "__import__",
    "__dict__",
    "__mro__",
    "__getattribute__",
    "__setattr__",
    "__delattr__",
}


ALLOWED_NODES = {
    # Structure
    ast.Module,
    ast.Expr,
    ast.Assign,
    ast.AnnAssign,
    ast.AugAssign,

    # Variables
    ast.Name,
    ast.Load,
    ast.Store,

    # Values
    ast.Constant,
    ast.List,
    ast.Tuple,
    ast.Dict,
    ast.Set,

    # Indexing / slicing
    ast.Subscript,
    ast.Attribute,
    ast.Slice,

    # Calls
    ast.Call,
    ast.keyword,

    # Operators
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.IfExp,

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
    ast.BitXor,

    # Membership
    ast.In,
    ast.NotIn,

    # Loops / comprehensions
    ast.For,
    ast.comprehension,
    ast.ListComp,
    ast.DictComp,
    ast.GeneratorExp,

    # Lambda
    ast.Lambda,

    # Conditional control
    ast.If,

    # Function returns inside lambda-related syntax
    ast.arguments,
    ast.arg,

    # Tuple/list unpacking
    ast.Starred,
}


class SafetyValidator(ast.NodeVisitor):
    """
    Validates generated Python before execution.

    This is a restricted execution layer, not a perfect security sandbox.
    """

    def visit(self, node):
        if type(node) not in ALLOWED_NODES:
            raise ValueError(
                f"Blocked Python operation: {type(node).__name__}"
            )

        return super().visit(node)

    def visit_Name(self, node):
        if node.id in BLOCKED_NAMES:
            raise ValueError(f"Blocked name: {node.id}")

        # Allow normal user-defined variables while preventing
        # dangerous names.
        return self.generic_visit(node)

    def visit_Attribute(self, node):
        if node.attr in BLOCKED_ATTRIBUTES:
            raise ValueError(
                f"Blocked attribute access: {node.attr}"
            )

        if node.attr.startswith("__"):
            raise ValueError(
                f"Blocked attribute access: {node.attr}"
            )

        return self.generic_visit(node)

    def visit_keyword(self, node):
        # Allow normal keyword arguments such as:
        # groupby(..., as_index=False)
        # px.bar(..., title="...")
        #
        # But reject dangerous **kwargs expansion.
        if node.arg is None:
            raise ValueError(
                "Blocked dictionary expansion in function call"
            )

        return self.generic_visit(node)


def validate_code(code):
    """
    Parse and validate generated Python code.
    """
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as error:
        raise ValueError(
            f"Generated code contains invalid Python syntax: {error}"
        )

    validator = SafetyValidator()
    validator.visit(tree)

    return tree


def execute_analysis(code, df):
    """
    Validate and execute generated analysis code.

    Expected generated variables:
        result -> final answer
        fig    -> optional Plotly figure
    """

    tree = validate_code(code)

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
    }

    try:
        exec(
            compile(tree, "<generated_analysis>", "exec"),
            safe_globals,
            safe_locals,
        )
    except Exception as error:
        raise RuntimeError(
            f"Generated code execution failed: {error}"
        )

    result = safe_locals.get("result")
    fig = safe_locals.get("fig")

    if result is None and "result" not in safe_locals:
        raise ValueError(
            "Generated code did not create a `result` variable."
        )

    return result, fig