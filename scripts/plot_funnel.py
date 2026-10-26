"""Draw the expected-vs-actual funnel plot for one year.

Input: the CSV from `python -m pipeline.ml_expected --csv <file>`.
Output: docs/images/06-funnel-plot.png (for the README and the website).
Needs matplotlib and pandas (a laptop tool, not part of the pipeline image).

    python scripts/plot_funnel.py ml_expected_oof.csv [--year 2024]
"""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

# Project theme (powerbi/qld-hospital-theme.json)
NAVY, TEAL, GREY, INK, MUTED = "#1F2A44", "#0F7C8C", "#9AA5B1", "#1F2A44", "#5B6775"
Z_95, Z_998 = 1.96, 3.09
OUT = Path("docs/images/06-funnel-plot.png")


def funnel_curve(df: pd.DataFrame, n: np.ndarray) -> np.ndarray:
    """Limit sd for a hospital with n presentations, at the year's median expected value.
    tau (the hospital-to-hospital spread) is backed out of the stored 95% limits."""
    p = np.clip(df["expected"] / 100, 0.01, 0.99)
    se2 = (100 ** 2) * p * (1 - p) / df["ed_presentations"]
    tau2 = float(np.median((df["limit_95"] / Z_95) ** 2 - se2))
    p_mid = float(np.median(p))
    return np.sqrt((100 ** 2) * p_mid * (1 - p_mid) / n + max(tau2, 0.0))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--year", type=int, help="financial year start, e.g. 2024 for 2024-25 (default: latest)")
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    year = args.year or int(df["fy_start_year"].max())
    d = df[df["fy_start_year"] == year].copy()
    label = d["period_label"].iloc[0]
    qld = d["state"] == "Qld"
    flagged = d["flag"] != "within expected range"

    plt.rcParams.update({"font.family": "Segoe UI", "font.size": 10})
    fig, ax = plt.subplots(figsize=(10, 6.2), dpi=200)
    fig.patch.set_facecolor("white")

    n = np.logspace(np.log10(d["ed_presentations"].min() * 0.8), np.log10(d["ed_presentations"].max() * 1.2), 200)
    sd = funnel_curve(df, n)
    for z, style in ((Z_998, "-"), (Z_95, "--")):
        ax.plot(n, z * sd, style, color=MUTED, lw=1.2)
        ax.plot(n, -z * sd, style, color=MUTED, lw=1.2)
    ax.axhline(0, color=NAVY, lw=1)

    ax.scatter(d.loc[~qld, "ed_presentations"], d.loc[~qld, "residual"], s=28,
               color=GREY, alpha=0.75, edgecolor="white", linewidth=0.6, zorder=2)
    ax.scatter(d.loc[qld, "ed_presentations"], d.loc[qld, "residual"], s=40,
               color=TEAL, edgecolor="white", linewidth=0.8, zorder=3)
    ax.scatter(d.loc[flagged, "ed_presentations"], d.loc[flagged, "residual"], s=95,
               facecolor="none", edgecolor=NAVY, linewidth=1.6, zorder=4)

    # Label Queensland's flagged hospitals and Toowoomba, set off to the left with a leader line
    to_label = d[(qld & flagged) | d["reporting_unit_name"].str.startswith("Toowoomba")]
    for _, r in to_label.iterrows():
        name = r["reporting_unit_name"].replace(" Hospital", "").replace(" Base", "")
        ax.annotate(f"{name}: {r['pct_within_4h']:.0f}% vs {r['expected']:.0f}% expected",
                    (r["ed_presentations"], r["residual"]),
                    xytext=(-60, 26 if r["residual"] >= 0 else -34), textcoords="offset points",
                    ha="right", va="center", fontsize=9, color=INK,
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none", alpha=0.9),
                    arrowprops=dict(arrowstyle="-", color=INK, lw=0.8, shrinkA=0, shrinkB=5), zorder=5)

    ax.set_xscale("log")
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v / 1000:g}k" if v >= 1000 else f"{v:g}"))
    ax.set_xlabel("ED presentations in the year (log scale)", color=MUTED)
    ax.set_ylabel("Actual minus expected (percentage points)", color=MUTED)
    lim = max(abs(d["residual"]).max(), Z_998 * sd.max()) * 1.12
    ax.set_ylim(-lim, lim)
    ax.grid(axis="y", color="#E6E9ED", lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#C9D0D7")
    ax.tick_params(colors=MUTED)

    n_above = int((d["flag"] == "well above expected").sum())
    n_below = int((d["flag"] == "well below expected").sum())
    fig.text(0.06, 0.955, f"Which hospitals are clearly above or below expected? {label}",
             fontsize=14, fontweight="bold", color=INK)
    fig.text(0.06, 0.915,
             f"% of ED patients leaving within 4 hours, against what's expected for the hospital's size and patient mix. "
             f"{len(d)} hospitals: {n_above} well above, {n_below} well below.",
             fontsize=10, color=MUTED)

    handles = [
        Line2D([], [], marker="o", ls="", color=GREY, markeredgecolor="white", markersize=7, label="Other Australian hospitals"),
        Line2D([], [], marker="o", ls="", color=TEAL, markeredgecolor="white", markersize=7, label="Queensland hospitals"),
        Line2D([], [], marker="o", ls="", markerfacecolor="none", markeredgecolor=NAVY, markeredgewidth=1.6,
               markersize=10, label="Outside 99.8% limits (flagged)"),
        Line2D([], [], ls="--", color=MUTED, label="95% limits"),
        Line2D([], [], ls="-", color=MUTED, label="99.8% limits"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=5, frameon=False,
              fontsize=9, labelcolor=INK, handletextpad=0.4, columnspacing=1.4)

    fig.text(0.06, 0.02,
             "Above zero = more patients left within 4 hours than expected. Expected values come from a model that never saw "
             "that hospital.\nA flag shows where to look, not a quality score. Source: AIHW MyHospitals, CC BY 3.0 AU.",
             fontsize=8.5, color=MUTED)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.2)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor="white")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
