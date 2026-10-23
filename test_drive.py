"""绘制最高支持三维变量的数学表达式图像。"""

import os
import re
import sys
from pathlib import Path


# 旧版 Anaconda NumPy 在启动时需要显式扫描自己的私有 DLL 与 Conda DLL。
if sys.platform == "win32":
    anaconda_dir = Path(sys.executable).parent
    numpy_dir = anaconda_dir / "Lib" / "site-packages" / "numpy"
    dll_dirs = (
        anaconda_dir,
        anaconda_dir / "Library" / "bin",
        anaconda_dir / "DLLs",
        numpy_dir / ".libs",
    )
    search_path = os.pathsep.join(str(path) for path in dll_dirs if path.is_dir())
    os.environ["PATH"] = search_path + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        for dll_dir in dll_dirs:
            if dll_dir.is_dir():
                os.add_dll_directory(str(dll_dir))

import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    parse_expr,
    standard_transformations,
)


TRANSFORMATIONS = standard_transformations + (convert_xor,)
ALLOWED_FUNCTIONS = {
    "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
    "sinh", "cosh", "tanh", "exp", "log", "ln", "sqrt", "abs",
}
ALLOWED_CONSTANTS = {"pi", "e"}


def suggest_expression(expression: str) -> str:
    suggested = expression.strip()
    suggested = re.sub(r"^\s*[A-Za-z_]\w*\s*=\s*", "", suggested, count=1)
    suggested = suggested.replace("^", "**")

    function_names = "sin|cos|tan|asin|acos|atan|atan2|sinh|cosh|tanh|exp|log|ln|sqrt|abs"
    suggested = re.sub(
        rf"\b({function_names})\s+([A-Za-z_]\w*)\b",
        r"\1(\2)",
        suggested,
    )
    suggested = re.sub(
        rf"\b(ln|log)([A-Za-z_]\w*)\b",
        lambda match: f"{match.group(1)}({match.group(2)})",
        suggested,
    )
    suggested = re.sub(r"(?<!\w)(\d+(?:\.\d+)?)\s*(?=[A-Za-z_]\w*)", r"\1*", suggested)
    suggested = re.sub(r"(?<=\d)\s+(?=[A-Za-z_]\w*)", "*", suggested)
    return re.sub(r"\s+", "", suggested)


def normalize_expression(expression: str) -> str:
    candidate = suggest_expression(expression)
    try:
        parse_expression(candidate)
        return candidate
    except (ValueError, SyntaxError, TypeError, NotImplementedError):
        return expression


def prompt_expression() -> str:
    expression = input("请输入数学表达式（例如 sin(x) + 0.2*x**2）：").strip()
    if not expression:
        raise ValueError("表达式不能为空")
    return expression


def parse_expression(expression: str):
    local_dict = {
        name: sp.Abs if name == "abs" else getattr(sp, name)
        for name in ALLOWED_FUNCTIONS
    }
    local_dict.update({"ln": sp.log, "pi": sp.pi, "e": sp.E})
    parsed = parse_expr(
        expression,
        local_dict=local_dict,
        transformations=TRANSFORMATIONS,
        evaluate=True,
    )

    variables = sorted(parsed.free_symbols, key=lambda symbol: symbol.name)
    if not variables:
        raise ValueError("表达式中至少需要一个变量")
    if len(variables) > 3:
        raise ValueError("最多支持三个变量")

    allowed_names = {symbol.name for symbol in variables}
    unknown_names = {
        token for token in re.findall(r"[A-Za-z_]\\w*", expression)
        if token not in allowed_names
        and token not in ALLOWED_FUNCTIONS
        and token not in ALLOWED_CONSTANTS
    }
    if unknown_names:
        raise ValueError(f"发现不允许的符号或函数：{', '.join(sorted(unknown_names))}")

    return parsed, variables


def suggest_domain(domain_text: str, variables) -> str:
    suggested = domain_text.strip().replace("；", ";")
    symbols = sorted((variable.name for variable in variables), key=len, reverse=True)
    for symbol in symbols:
        suggested = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(symbol)}\s*[=,:]", f"{symbol}=", suggested)
    suggested = re.sub(r"\bpi\b", str(float(np.pi)), suggested)
    suggested = re.sub(r"(?<![A-Za-z0-9_])-e\b", str(-float(np.e)), suggested)
    suggested = re.sub(r"(?<![A-Za-z0-9_])e\b", str(float(np.e)), suggested)
    suggested = re.sub(r"\s*[,，]\s*", ",", suggested)
    suggested = re.sub(r"\s*([;])\s*", r";", suggested)
    return suggested


def parse_domain(domain_text: str, variables) -> dict:
    text = domain_text.strip()
    if not text:
        raise ValueError("定义域不能为空")

    pieces = re.findall(
        r"[A-Za-z_]\w*\s*(?:=|in)\s*\[?\s*"
        r"[-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?\s*,\s*"
        r"[-+]?\d+(?:\.\d*)?(?:[eE][-+]?\d+)?\s*\]?",
        text,
    )
    if len(pieces) != len(variables):
        raise ValueError(f"需要为 {len(variables)} 个变量分别输入区间")

    domains = {}
    number = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
    domain_pattern = re.compile(
        rf"^\s*([A-Za-z_]\w*)\s*(?:=|in)\s*\[?\s*"
        rf"({number})\s*,\s*({number})\s*\]?\s*$"
    )
    for piece in variables:
        del piece

    available = {variable.name: variable for variable in variables}
    for piece in pieces:
        match = domain_pattern.match(piece)
        if not match:
            raise ValueError("区间格式应为：x=-10,10 或 x in [-10,10]")
        name, lower_text, upper_text = match.groups()
        if name not in available:
            raise ValueError(f"未知变量：{name}")
        lower, upper = float(lower_text), float(upper_text)
        if not np.isfinite(lower) or not np.isfinite(upper):
            raise ValueError("区间端点必须是有限数")
        if lower >= upper:
            raise ValueError(f"变量 {name} 的下限必须小于上限")
        domains[name] = (lower, upper)

    if set(domains) != set(available):
        missing = sorted(set(available) - set(domains))
        raise ValueError(f"缺少变量定义域：{', '.join(missing)}")
    return domains


def prompt_domain(variables) -> dict:
    print("变量区间格式示例：x=-10,10 或 x=-10,10; y=-5,5; z=-3,3")
    names = ", ".join(sorted(symbol.name for symbol in variables))
    text = input(f"请输入 {names} 的定义域：")
    try:
        return parse_domain(text, variables)
    except (ValueError, SyntaxError, TypeError) as error:
        candidate = suggest_domain(text, variables)
        try:
            domains = parse_domain(candidate, variables)
        except (ValueError, SyntaxError, TypeError):
            raise error
        print(f"已识别原定义域：{text}")
        print(f"建议直接粘贴：{candidate}")
        if input("使用建议定义域？(yes/no)：").strip().lower() == "no":
            raise error
        return domains


def numpy_function(parsed, variables):
    function = sp.lambdify(variables, parsed, modules=["numpy"])

    def evaluate(*values):
        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            result = np.asarray(function(*values), dtype=float)
        return np.where(np.isfinite(result), result, np.nan)

    return evaluate


def load_matplotlib():
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    return plt


def plot_one_variable(parsed, variables, domains):
    variable = variables[0]
    lower, upper = domains[variable.name]
    x = np.linspace(lower, upper, 1000)
    y = numpy_function(parsed, variables)(x)

    figure, axis = plt.subplots()
    axis.plot(x, y, linewidth=2)
    axis.set_xlabel(variable.name)
    axis.set_ylabel(f"f({variable.name})")
    axis.set_title(f"$f({variable.name}) = {sp.latex(parsed)}$")
    axis.grid(True, alpha=0.35)
    axis.axhline(0, color="black", linewidth=0.7, alpha=0.5)
    return figure


def plot_two_variables(parsed, variables, domains):
    first, second = variables
    x_limits = domains[first.name]
    y_limits = domains[second.name]
    x = np.linspace(*x_limits, 150)
    y = np.linspace(*y_limits, 150)
    x_grid, y_grid = np.meshgrid(x, y)
    z_grid = numpy_function(parsed, variables)(x_grid, y_grid)

    figure = plt.figure()
    axis = figure.add_subplot(111, projection="3d")
    surface = axis.plot_surface(
        x_grid,
        y_grid,
        z_grid,
        cmap="viridis",
        rcount=100,
        ccount=100,
        linewidth=0,
        antialiased=True,
    )
    axis.set_xlabel(first.name)
    axis.set_ylabel(second.name)
    axis.set_zlabel(f"f({first.name}, {second.name})")
    axis.set_title(f"$f = {sp.latex(parsed)}$")
    figure.colorbar(surface, ax=axis, shrink=0.7, label="value")
    return figure


def plot_three_variables(parsed, variables, domains):
    x_limits = domains[variables[0].name]
    y_limits = domains[variables[1].name]
    z_limits = domains[variables[2].name]
    x_axis = np.linspace(*x_limits, 24)
    y_axis = np.linspace(*y_limits, 24)
    z_axis = np.linspace(*z_limits, 24)
    x_grid, y_grid, z_grid = np.meshgrid(x_axis, y_axis, z_axis, indexing="ij")
    values = numpy_function(parsed, variables)(x_grid, y_grid, z_grid)

    finite = np.isfinite(values)
    if not finite.any():
        raise ValueError("在所给定义域内没有可绘制的有限函数值")

    percentile = np.nanpercentile(np.abs(values), 97)
    mask = finite & (np.abs(values) >= percentile)
    if mask.sum() < 5:
        mask = finite

    figure = plt.figure()
    axis = figure.add_subplot(111, projection="3d")
    scatter = axis.scatter(
        x_grid[mask], y_grid[mask], z_grid[mask],
        c=values[mask], cmap="coolwarm", s=18,
        alpha=0.8, edgecolors="none",
    )
    axis.set_xlabel(variables[0].name)
    axis.set_ylabel(variables[1].name)
    axis.set_zlabel(variables[2].name)
    axis.set_title(f"3D point cloud (color = $f = {sp.latex(parsed)}$)")
    figure.colorbar(scatter, ax=axis, shrink=0.7, label="value")
    return figure


def draw_expression(expression: str, domain_text: str):
    parsed, variables = parse_expression(expression)
    domains = parse_domain(domain_text, variables)
    plotters = (
        plot_one_variable,
        plot_two_variables,
        plot_three_variables,
    )
    figure = plotters[len(variables) - 1](parsed, variables, domains)
    figure.tight_layout()
    return figure


def main() -> None:
    global plt
    plt = load_matplotlib()
    print("数学表达式绘图器")
    while True:
        try:
            expression = prompt_expression()
            try:
                parsed, variables = parse_expression(expression)
                candidate = expression
            except (ValueError, SyntaxError, TypeError, NotImplementedError) as error:
                candidate = normalize_expression(expression)
                if candidate != expression:
                    try:
                        parsed, variables = parse_expression(candidate)
                        print(f"已识别原输入：{expression}")
                        print(f"建议直接粘贴：{candidate}")
                        if input("使用建议表达式？(yes/no)：").strip().lower() == "no":
                            raise error
                        expression = candidate
                    except (ValueError, SyntaxError, TypeError, NotImplementedError):
                        raise error
                else:
                    raise error

            print("识别变量：", ", ".join(symbol.name for symbol in variables))
            domains = prompt_domain(variables)
            draw_expression(expression, format_domain(domains, variables))
            plt.show(block=True)
        except (ValueError, SyntaxError, TypeError, NotImplementedError) as error:
            print(f"输入错误：{error}")
        except ArithmeticError as error:
            print(f"表达式无法计算：{error}")

        if input("继续绘制另一表达式？(y/N)：").strip().lower() not in {"y", "yes"}:
            break


def format_domain(domains: dict, variables) -> str:
    return ",".join(
        f"{variable.name}={lower},{upper}"
        for variable in variables
        for lower, upper in (domains[variable.name],)
    )


if __name__ == "__main__":
    main()
