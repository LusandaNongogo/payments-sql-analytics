"""Dashboard preview charts from the query outputs.

    py -m src.charts
"""

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

from src.build_db import ROOT

OUT = ROOT / "outputs"
FIG = ROOT / "reports" / "figures"
BLUE, ORANGE, GREY = "#1f4e79", "#c55a11", "#9e9e9e"


def _style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(alpha=0.25)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(2, 2, figsize=(14, 9))

    k = pd.read_csv(OUT / "11_daily_kpis.csv", parse_dates=["day"])
    a = ax[0, 0]
    a.plot(k["day"], k["value"] / 1e6, color=GREY, lw=1, label="Daily")
    a.plot(k["day"], k["value_7d_avg"] / 1e6, color=BLUE, lw=2, label="7 day average")
    a.set(title="Successful payment value (R million)", ylabel="R million")
    a.xaxis.set_major_locator(mdates.MonthLocator())
    a.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    a.legend()
    _style(a)

    f = pd.read_csv(OUT / "04_failure_rates.csv")
    f = f[f["channel"] == "card"].sort_values("failure_rate_pct")
    a = ax[0, 1]
    colors = [ORANGE if b == "Bank F" else BLUE for b in f["issuing_bank"]]
    a.barh(f["issuing_bank"], f["failure_rate_pct"], color=colors)
    for y, (rate, share) in enumerate(zip(f["failure_rate_pct"], f["timeout_share_pct"])):
        a.text(rate + 0.2, y, f"{rate:.1f}%  ({share:.0f}% timeouts)", va="center", fontsize=9)
    a.set(title="Card failure rate by issuing bank", xlabel="Failure rate %",
          xlim=(0, f["failure_rate_pct"].max() * 1.6))
    _style(a)

    r = pd.read_csv(OUT / "07_retry_recovery.csv").sort_values("recovery_rate_pct")
    a = ax[1, 0]
    a.barh(r["failure_reason"].str.replace("_", " "), r["recovery_rate_pct"], color=BLUE)
    a.set(title="Failed payments recovered by a retry within 15 minutes", xlabel="Recovered %")
    _style(a)

    rc = pd.read_csv(OUT / "01_recon_summary.csv").sort_values("value_at_stake")
    a = ax[1, 1]
    a.barh(rc["exception_type"].str.replace("_", " "), rc["value_at_stake"] / 1e3, color=ORANGE)
    for y, (v, n) in enumerate(zip(rc["value_at_stake"], rc["exceptions"])):
        a.text(v / 1e3 + 1, y, f"{n} items", va="center", fontsize=9)
    a.set(title="Reconciliation exceptions by value", xlabel="R thousand",
          xlim=(0, rc["value_at_stake"].max() / 1e3 * 1.3))
    _style(a)

    plt.tight_layout()
    fig.savefig(FIG / "dashboard_preview.png", dpi=150, bbox_inches="tight")
    print(f"saved {FIG / 'dashboard_preview.png'}")


if __name__ == "__main__":
    main()
