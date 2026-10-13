import ast
import ctypes
import os
import sys
import threading

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


# Methods that write files, read files, evaluate strings as code, or can be
# used to walk out of the allowed objects. Blocked as attributes. Writers
# and eval/query are also blocked as plain text values, because pandas can
# call a method by its name, for example df.apply("to_csv", ...).
BLOCKED_METHODS = {
    # writers
    "to_csv", "to_excel", "to_pickle", "to_sql", "to_parquet",
    "to_feather", "to_hdf", "to_json", "to_html", "to_latex", "to_xml",
    "to_clipboard", "to_orc", "to_stata", "to_gbq", "to_markdown",
    "to_string", "savefig", "show",
    # evaluate strings as code
    "eval", "query",
    # reach other modules / objects
    "format", "format_map", "mro", "style", "plot", "io", "compat",
    "os", "sys", "subprocess", "system", "popen", "environ",
}

BLOCKED_METHOD_PREFIXES = ("read_", "write_")

# Smaller list for plain text values, so a column called "style" or
# "format" can still be used.
BLOCKED_STRING_VALUES = {
    "to_csv", "to_excel", "to_pickle", "to_sql", "to_parquet",
    "to_feather", "to_hdf", "to_json", "to_html", "to_latex", "to_xml",
    "to_clipboard", "to_orc", "to_stata", "to_gbq", "to_markdown",
    "to_string", "savefig", "eval", "query",
}


# --- what pd / px / go may expose --------------------------------------
# Without this, code like pd.io.common.os.system("...") passes the AST
# check (it is only attribute access and a call) and runs a shell command.

MODULE_NAMES = {"pd", "px", "go"}

ALLOWED_PD_ATTRIBUTES = {
    "DataFrame", "Series", "Index", "MultiIndex", "DatetimeIndex",
    "PeriodIndex", "IntervalIndex", "Categorical", "CategoricalDtype",
    "Timestamp", "Timedelta", "Period", "Interval", "DateOffset",
    "Grouper", "NamedAgg", "NA", "NaT", "concat", "merge", "merge_asof",
    "cut", "qcut", "to_datetime", "to_numeric", "to_timedelta", "isna",
    "isnull", "notna", "notnull", "date_range", "period_range",
    "timedelta_range", "interval_range", "pivot_table", "pivot",
    "crosstab", "melt", "wide_to_long", "get_dummies", "unique",
    "factorize", "value_counts", "array", "api",
}

ALLOWED_PX_ATTRIBUTES = {
    "scatter", "scatter_3d", "scatter_polar", "scatter_ternary",
    "scatter_geo", "scatter_matrix", "line", "line_3d", "line_polar",
    "line_geo", "area", "bar", "bar_polar", "pie", "sunburst", "treemap",
    "icicle", "funnel", "funnel_area", "histogram", "box", "violin",
    "strip", "ecdf", "density_heatmap", "density_contour", "imshow",
    "parallel_coordinates", "parallel_categories", "choropleth",
    "timeline", "colors",
}

PX_COLOR_MODULES = {"qualitative", "sequential", "diverging", "cyclical"}


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
    ast.JoinedStr,
    ast.FormattedValue,

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
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,

    ast.USub,
    ast.UAdd,
    ast.Not,
    ast.Invert,

    ast.And,
    ast.Or,

    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.Is,
    ast.IsNot,

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
    ast.SetComp,
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


def _module_path(node):
    """
    For pd.a.b.c return ("pd", ["a", "b", "c"]).
    Returns None when the chain does not start at a plain name.
    """
    attributes = []

    while isinstance(node, ast.Attribute):
        attributes.append(node.attr)
        node = node.value

    if isinstance(node, ast.Name):
        return node.id, list(reversed(attributes))

    return None


def _check_module_path(root, path):
    first = path[0]

    if root == "pd":

        if first == "api":
            # only pd.api.types.is_*_dtype style helpers
            if (
                len(path) > 3
                or (len(path) >= 2 and path[1] != "types")
                or (len(path) == 3 and not path[2].startswith("is_"))
            ):
                raise ValueError(
                    f"Blocked access: {root}.{'.'.join(path)}"
                )

        elif first not in ALLOWED_PD_ATTRIBUTES:
            raise ValueError(f"Blocked access: {root}.{first}")

    elif root == "px":

        if first == "colors":
            if len(path) > 3 or (
                len(path) >= 2 and path[1] not in PX_COLOR_MODULES
            ):
                raise ValueError(
                    f"Blocked access: {root}.{'.'.join(path)}"
                )

        elif first not in ALLOWED_PX_ATTRIBUTES or len(path) > 1:
            raise ValueError(f"Blocked access: {root}.{first}")

    elif root == "go":

        # go.Figure, go.Bar, go.Scatter ... (classes only)
        if len(path) > 1 or not first[:1].isupper():
            raise ValueError(f"Blocked access: {root}.{first}")


class SafetyValidator(ast.NodeVisitor):
    """
    Validates generated Python before execution.

    This is a restricted execution layer, not a perfect security sandbox.
    """

    def __init__(self):
        self._module_names_in_use = set()

    def visit(self, node):
        if type(node) not in ALLOWED_NODES:
            raise ValueError(
                f"Blocked Python operation: {type(node).__name__}"
            )

        return super().visit(node)

    def visit_Name(self, node):
        if node.id in BLOCKED_NAMES:
            raise ValueError(f"Blocked name: {node.id}")

        # pd / px / go may only be used as pd.something. Passing the bare
        # module around (m = pd) would hide later pd.io... style access.
        if (
            node.id in MODULE_NAMES
            and id(node) not in self._module_names_in_use
        ):
            raise ValueError(
                f"Use {node.id}.<function> directly; "
                f"`{node.id}` cannot be used on its own"
            )

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

        if (
            node.attr in BLOCKED_METHODS
            or node.attr.startswith(BLOCKED_METHOD_PREFIXES)
        ):
            raise ValueError(
                f"Blocked attribute access: {node.attr}"
            )

        module_path = _module_path(node)

        if module_path is not None:

            root, path = module_path

            if root in MODULE_NAMES:
                _check_module_path(root, path)

                # remember the Name node at the bottom of this chain
                inner = node
                while isinstance(inner, ast.Attribute):
                    inner = inner.value
                self._module_names_in_use.add(id(inner))

        return self.generic_visit(node)

    def visit_BinOp(self, node):
        # 9 ** 9 ** 9 would keep Python busy for hours. A chained power
        # or a huge constant exponent is never needed for business maths.
        if isinstance(node.op, ast.Pow):

            for side in (node.left, node.right):
                if isinstance(side, ast.BinOp) and isinstance(side.op, ast.Pow):
                    raise ValueError(
                        "Blocked: chained powers (a ** b ** c)"
                    )

            exponent = node.right

            if (
                isinstance(exponent, ast.Constant)
                and isinstance(exponent.value, (int, float))
                and abs(exponent.value) > 1000
            ):
                raise ValueError("Blocked: exponent is too large")

        return self.generic_visit(node)

    def visit_AugAssign(self, node):
        # x **= y skips the power guard; plain x = x ** y is allowed
        if isinstance(node.op, ast.Pow):
            raise ValueError("Blocked: use x = x ** y instead of x **= y")

        return self.generic_visit(node)

    def visit_Constant(self, node):
        # df.apply("to_csv", args=(path,)) calls a method by its name.
        # (read_* / write_* are not listed here: no DataFrame method has
        # such a name, and column names like "write_off" are legitimate.)
        if isinstance(node.value, str) and node.value in BLOCKED_STRING_VALUES:
            raise ValueError(
                f"Blocked text value: {node.value!r}"
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


# ============================================================
# Runtime guard
# ============================================================
#
# The checks above look at the code before it runs. This guard watches
# what the running code actually does and refuses to start programs,
# open network connections, or write / delete files, even if a
# trick gets past the checks above. It only applies on the thread that
# is currently running generated code.

if not hasattr(sys, "_analysis_guard_state"):
    sys._analysis_guard_state = threading.local()


_BLOCKED_EVENT_PREFIXES = (
    "os.system",
    "os.exec",
    "os.spawn",
    "os.posix_spawn",
    "os.fork",
    "os.remove",
    "os.rename",
    "os.rmdir",
    "os.mkdir",
    "os.truncate",
    "os.chmod",
    "os.chown",
    "os.symlink",
    "os.link",
    "os.putenv",
    "os.unsetenv",
    "subprocess.",
    "socket.",
    "ctypes.",
    "urllib.",
    "http.client.",
    "ftplib.",
    "smtplib.",
    "shutil.",
    "pickle.find_class",
    "webbrowser.",
)

_WRITE_FLAGS = (
    os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
)


def _audit_hook(event, args):

    state = sys._analysis_guard_state

    if not getattr(state, "active", False):
        return

    if event == "open":

        mode = args[1] if len(args) > 1 else None
        flags = args[2] if len(args) > 2 else None

        if isinstance(mode, str) and any(c in mode for c in "wax+"):
            raise PermissionError(
                "Blocked: generated code may not write files"
            )

        if isinstance(flags, int) and flags & _WRITE_FLAGS:
            raise PermissionError(
                "Blocked: generated code may not write files"
            )

        return

    if event.startswith(_BLOCKED_EVENT_PREFIXES):
        raise PermissionError(
            f"Blocked: generated code may not use {event}"
        )


if not getattr(sys, "_analysis_guard_installed", False):
    sys.addaudithook(_audit_hook)
    sys._analysis_guard_installed = True


# Plain helpers that are safe to give to generated code.
SAFE_BUILTINS = {
    "len": len,
    "int": int,
    "float": float,
    "str": str,
    "round": round,
    "abs": abs,
    "min": min,
    "max": max,
    "sum": sum,
    "sorted": sorted,
    "list": list,
    "dict": dict,
    "set": set,
    "tuple": tuple,
    "bool": bool,
    "range": range,
    "zip": zip,
    "enumerate": enumerate,
    "any": any,
    "all": all,
}


# ============================================================
# Time limit
# ============================================================
#
# Generated code that loops for too long is stopped after MAX_SECONDS.
# This catches runaway Python loops. It cannot interrupt one single huge
# calculation that never returns to Python (for example a giant integer
# power built from variables), so a public deployment should also run the
# analysis in a separate process or container.

MAX_SECONDS = 30


class AnalysisTimeout(BaseException):
    """
    Raised inside generated code when it runs too long. It is a
    BaseException so that `except Exception` inside pandas cannot
    swallow it and carry on.
    """


def _safe_pow(base, exponent):
    """
    a ** b for generated code. Only plain Python whole numbers can grow
    without limit, so only those are checked. Floats, numpy and pandas
    values go straight through.
    """

    if (
        type(base) is int
        and type(exponent) is int
        and exponent > 0
        and base.bit_length() * exponent > 2_000_000
    ):
        raise ValueError(
            "Blocked: this power would produce an enormous number"
        )

    return base ** exponent


class _PowGuard(ast.NodeTransformer):
    """Rewrites every `a ** b` into `_safe_pow(a, b)` after validation."""

    def visit_BinOp(self, node):

        self.generic_visit(node)

        if isinstance(node.op, ast.Pow):
            return ast.copy_location(
                ast.Call(
                    func=ast.Name(id="_safe_pow", ctx=ast.Load()),
                    args=[node.left, node.right],
                    keywords=[],
                ),
                node,
            )

        return node


def _stop_thread(thread_id, finished):

    if finished.is_set():
        return

    ctypes.pythonapi.PyThreadState_SetAsyncExc(
        ctypes.c_ulong(thread_id),
        ctypes.py_object(AnalysisTimeout),
    )


def execute_analysis(code, df):
    """
    Validate and execute generated analysis code.

    Expected generated variables:
        result -> final answer
        fig    -> optional Plotly figure
    """

    tree = validate_code(code)

    # One namespace for everything. With separate globals and locals,
    # lambdas (and comprehensions on older Python) cannot see `df` or
    # variables the code defined earlier.
    tree = ast.fix_missing_locations(_PowGuard().visit(tree))

    namespace = {
        "__builtins__": dict(SAFE_BUILTINS),
        "pd": pd,
        "px": px,
        "go": go,
        "df": df.copy(),
        "_safe_pow": _safe_pow,
    }

    state = sys._analysis_guard_state
    state.active = True

    thread_id = threading.get_ident()
    finished = threading.Event()

    watchdog = threading.Timer(
        MAX_SECONDS, _stop_thread, args=(thread_id, finished)
    )
    watchdog.daemon = True
    watchdog.start()

    try:
        exec(
            compile(tree, "<generated_analysis>", "exec"),
            namespace,
        )
    except AnalysisTimeout:
        raise RuntimeError(
            f"The analysis ran for more than {MAX_SECONDS} seconds and "
            "was stopped. Ask for something simpler or narrower."
        )
    except Exception as error:
        raise RuntimeError(
            f"Generated code execution failed: {error}"
        )
    finally:
        finished.set()
        watchdog.cancel()
        state.active = False

        # if the alarm went off at the last moment, take it back
        ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_ulong(thread_id), None
        )

    result = namespace.get("result")
    fig = namespace.get("fig")

    if result is None and "result" not in namespace:
        raise ValueError(
            "Generated code did not create a `result` variable."
        )

    return result, fig
