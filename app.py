"""本地或公网可访问的数学表达式网页绘图器。"""

import json
import os

import test_drive as plotter

import numpy as np
import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder
from flask import Flask, jsonify, render_template, request


app = Flask(__name__)


def build_plot(expression: str, domain_text: str):
    parsed, variables = plotter.parse_expression(expression)
    domains = plotter.parse_domain(domain_text, variables)
    evaluate = plotter.numpy_function(parsed, variables)

    if len(variables) == 1:
        name = variables[0].name
        x_values = np.linspace(*domains[name], 1000)
        y_values = evaluate(x_values)
        figure = go.Figure(go.Scatter(x=x_values, y=y_values, mode="lines", name="f(x)"))
        figure.update_layout(title="Curve", xaxis_title=name, yaxis_title="function value", template="plotly_white", height=640)
        return figure

    if len(variables) == 2:
        first, second = variables
        x_values = np.linspace(*domains[first.name], 180)
        y_values = np.linspace(*domains[second.name], 180)
        x_grid, y_grid = np.meshgrid(x_values, y_values)
        z_values = evaluate(x_grid, y_grid)
        figure = go.Figure(go.Surface(x=x_grid, y=y_grid, z=z_values, colorscale="Viridis"))
        figure.update_layout(title="Surface", scene={"xaxis_title": first.name, "yaxis_title": second.name, "zaxis_title": "function value"}, template="plotly_white", height=720)
        return figure

    first, second, third = variables
    x_values = np.linspace(*domains[first.name], 24)
    y_values = np.linspace(*domains[second.name], 24)
    z_values = np.linspace(*domains[third.name], 24)
    x_grid, y_grid, z_grid = np.meshgrid(x_values, y_values, z_values, indexing="ij")
    values = evaluate(x_grid, y_grid, z_grid)
    finite = np.isfinite(values)
    figure = go.Figure(go.Scatter3d(
        x=x_grid[finite], y=y_grid[finite], z=z_grid[finite],
        mode="markers",
        marker={"size": 2.8, "color": values[finite], "colorscale": "Portland", "opacity": 0.75},
    ))
    figure.update_layout(title="3D point cloud", scene={"xaxis_title": first.name, "yaxis_title": second.name, "zaxis_title": third.name}, template="plotly_white", height=720)
    return figure


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/api/plot", methods=["POST"])
def api_plot():
    data = request.get_json(silent=True) or {}
    expression = str(data.get("expression", "")).strip()
    domain = str(data.get("domain", "")).strip()

    try:
        figure = build_plot(expression, domain)
        payload = json.dumps({"ok": True, "figure": figure.to_dict()}, cls=PlotlyJSONEncoder)
        return app.response_class(payload, status=200, mimetype="application/json")
    except (ValueError, SyntaxError, TypeError, NotImplementedError) as error:
        suggested_expression = plotter.normalize_expression(expression)
        suggested_domain = None
        try:
            _, variables = plotter.parse_expression(suggested_expression)
            suggested_domain = plotter.suggest_domain(domain, variables)
            plotter.parse_domain(suggested_domain, variables)
        except (ValueError, SyntaxError, TypeError, NotImplementedError):
            suggested_domain = None
        return jsonify({
            "ok": False,
            "error": str(error),
            "suggested_expression": suggested_expression if suggested_expression != expression else None,
            "suggested_domain": suggested_domain,
        }), 400


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
