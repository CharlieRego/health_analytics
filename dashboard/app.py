"""Minimal Taipy test app: checks the dashboard runs on the server and how much memory it uses.

Uses a small made-up table, not real data. Replaced by the real pages later.
"""

import os

import pandas as pd
from taipy.gui import Gui

# Made-up numbers, only to draw a chart
SAMPLE = pd.DataFrame(
    {
        "year": ["2021", "2022", "2023", "2024", "2025"],
        "Hospital A": [66, 60, 52, 47, 44],
        "Hospital B": [71, 69, 66, 64, 63],
    }
)

hospitals = ["Hospital A", "Hospital B"]
hospital = hospitals[0]
chart_data = SAMPLE[["year", hospital]].rename(columns={hospital: "value"})


def on_change(state, var_name, value):
    # Runs in the browser session over the websocket when the selector changes
    if var_name == "hospital":
        state.chart_data = SAMPLE[["year", value]].rename(columns={value: "value"})


page = """
# Taipy test page

Test data only. Pick a hospital and the chart should update.

<|{hospital}|selector|lov={hospitals}|dropdown|>

<|{chart_data}|chart|type=bar|x=year|y=value|>
"""

if __name__ == "__main__":
    Gui(page).run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        title="QLD Hospital Performance (test)",
        run_browser=False,
        use_reloader=False,
        debug=False,
    )
