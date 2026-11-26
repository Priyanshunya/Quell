# Cylindrical slosh frequency and 3-impulse ZVD simulation.
# Used to sanity-check ZVD timings and +-14% frequency error before hardware tests.

import csv
import math
from pathlib import Path

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    PLOT_ENABLED = True
except ImportError:
    PLOT_ENABLED = False


G = 9.81

# Linear-rail move parameters (matched between unshaped and shaped runs)
STROKE_M = 0.25
A_MAX = 1.20       # m/s^2
V_MAX = 0.60       # m/s
DT = 0.0005        # 0.5 ms integration step
TAIL_S = 2.0       # settling window after motion stops

OFFSETS_PCT = list(range(-24, 25, 2))

VESSELS = [
    {
        "name": "Shallow liquid (R=40mm, h=15mm)",
        "short": "Shallow (h=15 mm)",
        "bucket": "shallow_liquid",
        "r": 0.040,
        "h": 0.015,
        "zeta": 0.010,
    },
    {
        "name": "Medium liquid (R=40mm, h=40mm)",
        "short": "Medium (h=40 mm)",
        "bucket": "medium_high_liquid",
        "r": 0.040,
        "h": 0.040,
        "zeta": 0.010,
    },
    {
        "name": "High liquid (R=40mm, h=70mm)",
        "short": "High (h=70 mm)",
        "bucket": "medium_high_liquid",
        "r": 0.040,
        "h": 0.070,
        "zeta": 0.012,
    },
]


def slosh_freq_hz(r, h):
    # First antisymmetric mode root for a rigid upright cylinder: xi_11 = 1.841
    w2 = (1.841 * G / r) * math.tanh(1.841 * h / r)
    return math.sqrt(w2) / (2.0 * math.pi)


def zvd_shaper(fn_hz, zeta):
    wn = 2.0 * math.pi * fn_hz
    d = math.sqrt(1.0 - zeta * zeta)
    td = 2.0 * math.pi / (wn * d)

    k = math.exp(-zeta * math.pi / d)
    denom = (1.0 + k) ** 2

    times = [0.0, 0.5 * td, td]
    weights = [1.0 / denom, (2.0 * k) / denom, (k * k) / denom]
    return times, weights


def trap_accel_profile(dist, amax, vmax, dt):
    # Standard trapezoidal (or triangular if stroke is short) acceleration command
    d_ramp = (vmax * vmax) / amax
    if dist >= d_ramp:
        t_acc = vmax / amax
        t_cruise = (dist - d_ramp) / vmax
    else:
        t_acc = math.sqrt(dist / amax)
        t_cruise = 0.0

    t_dec = t_acc + t_cruise
    t_move = 2.0 * t_acc + t_cruise

    n = int(math.ceil(t_move / dt)) + 1
    t = [i * dt for i in range(n)]
    a = [0.0] * n

    for i, ti in enumerate(t):
        if ti < t_acc:
            a[i] = amax
        elif ti < t_dec:
            a[i] = 0.0
        elif ti < t_move:
            a[i] = -amax

    return t, a, t_move


def convolve_with_shaper(t_base, a_base, imp_t, imp_w, tail_s, dt):
    t_end = t_base[-1] + max(imp_t) + tail_s
    n = int(math.ceil(t_end / dt)) + 1
    t_out = [i * dt for i in range(n)]
    a_out = [0.0] * n

    for delay, w in zip(imp_t, imp_w):
        shift = int(round(delay / dt))
        for i, val in enumerate(a_base):
            idx = i + shift
            if idx < n:
                a_out[idx] += w * val

    return t_out, a_out


def sim_slosh(t, a_cart, fn_hz, zeta, t_settle):
    # Linearized 2nd-order slosh mode: q'' + 2*zeta*wn*q' + wn^2*q = -a_cart
    # Semi-implicit Euler is stable and accurate enough at dt = 0.5 ms
    wn = 2.0 * math.pi * fn_hz
    wn2 = wn * wn
    c = 2.0 * zeta * wn

    q = 0.0
    qd = 0.0
    q_hist = []
    peak = 0.0
    resid = 0.0

    for i, ti in enumerate(t):
        q_hist.append(q)
        aq = abs(q)
        if aq > peak:
            peak = aq
        if ti >= t_settle and aq > resid:
            resid = aq

        if i < len(t) - 1:
            step = t[i + 1] - ti
            qdd = -a_cart[i] - c * qd - wn2 * q
            qd += qdd * step
            q += qd * step

    return q_hist, peak, resid


def reduction_pct(base_val, shaped_val):
    if base_val <= 0.0:
        return 0.0
    return (1.0 - shaped_val / base_val) * 100.0


def save_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def save_plots(sweep_rows, traces, mode_rows, fig_dir):
    fig_dir.mkdir(parents=True, exist_ok=True)

    plt.rcParams.update({
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })

    # 1. Time-domain response (medium fill case)
    ref = VESSELS[1]
    t, a_un, a_zv, q_un, q_zv = traces[ref["name"]]
    fn_ref = slosh_freq_hz(ref["r"], ref["h"])

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.5, 5.2), sharex=True)
    ax1.plot(t, a_un, color="#64748b", lw=1.5, ls="--", label="Unshaped trapezoidal")
    ax1.plot(t, a_zv, color="#0f766e", lw=1.8, label="3-impulse ZVD")
    ax1.set_ylabel("Cart accel (m/s^2)")
    ax1.set_title(f"{STROKE_M:.2f} m Move — {ref['name']} (fn = {fn_ref:.2f} Hz)")
    ax1.legend(loc="upper right")

    ax2.plot(t, [v * 1e3 for v in q_un], color="#dc2626", lw=1.4, alpha=0.85, label="Unshaped slosh")
    ax2.plot(t, [v * 1e3 for v in q_zv], color="#0f766e", lw=1.8, label="ZVD slosh")
    ax2.axhline(0.0, color="#334155", lw=0.8)
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Normalized slosh q (x10^-3)")
    ax2.legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(fig_dir / "time_response_ab.png", dpi=200)
    plt.close(fig)

    # 2. Frequency mismatch sensitivity (+-14% target window)
    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(9.5, 4.0))
    colors = ["#2563eb", "#0f766e", "#b45309"]

    for col, v in zip(colors, VESSELS):
        sub = [r for r in sweep_rows if r["case_name"] == v["name"]]
        xs = [r["freq_offset_pct"] for r in sub]
        ax_l.plot(xs, [r["peak_reduction_pct"] for r in sub], "o-", ms=3.5, lw=1.6, color=col, label=v["short"])
        ax_r.plot(xs, [r["resid_reduction_pct"] for r in sub], "o-", ms=3.5, lw=1.6, color=col, label=v["short"])

    for ax, title, ylabel in [
        (ax_l, "Peak Transient Reduction", "Peak reduction (%)"),
        (ax_r, "Post-Move Residual Reduction", "Residual reduction (%)"),
    ]:
        ax.axvspan(-14, 14, color="#0f766e", alpha=0.10, label="±14% band")
        ax.axhline(70.0, color="#dc2626", ls=":", lw=1.2, label="70% target")
        ax.set_title(title)
        ax.set_xlabel("Slosh frequency error (%)")
        ax.set_ylabel(ylabel)
        ax.set_ylim(35, 103)

    ax_r.legend(loc="lower center", fontsize=8.5)
    fig.tight_layout()
    fig.savefig(fig_dir / "sensitivity_curve.png", dpi=200)
    plt.close(fig)

    # 3. Fill aspect ratio sweep (h/R vs fn and shaper duration)
    ratios = [r["h_over_R"] for r in mode_rows]
    freqs = [r["fn_hz"] for r in mode_rows]
    td_ms = [r["zvd_duration_s"] * 1000.0 for r in mode_rows]

    fig, ax_f = plt.subplots(figsize=(7.8, 3.8))
    ax_t = ax_f.twinx()

    l1 = ax_f.plot(ratios, freqs, color="#0f766e", lw=2.0, label="Fundamental slosh fn (Hz)")
    l2 = ax_t.plot(ratios, td_ms, color="#b45309", lw=1.8, ls="--", label="ZVD duration Td (ms)")

    ax_f.set_xlabel("Fill aspect ratio (h / R) for R = 40 mm")
    ax_f.set_ylabel("Slosh frequency fn (Hz)", color="#0f766e")
    ax_t.set_ylabel("ZVD duration Td (ms)", color="#b45309")
    ax_t.spines["top"].set_visible(False)
    ax_f.set_title("Slosh Mode Frequency and ZVD Duration vs. Fill Depth")

    lines = l1 + l2
    ax_f.legend(lines, [ln.get_label() for ln in lines], loc="center right")
    fig.tight_layout()
    fig.savefig(fig_dir / "fill_depth_profile.png", dpi=200)
    plt.close(fig)


def main():
    base_dir = Path(__file__).resolve().parent
    t_base, a_base, t_move = trap_accel_profile(STROKE_M, A_MAX, V_MAX, DT)
    t_un_all, a_un_all = convolve_with_shaper(t_base, a_base, [0.0], [1.0], TAIL_S, DT)

    sweep_rows = []
    traces = {}

    print(f"Move: {STROKE_M:.2f} m | amax={A_MAX:.2f} m/s^2 | vmax={V_MAX:.2f} m/s\n")

    for v in VESSELS:
        fn_nom = slosh_freq_hz(v["r"], v["h"])
        zvd_t, zvd_w = zvd_shaper(fn_nom, v["zeta"])
        t_zv_all, a_zv_all = convolve_with_shaper(t_base, a_base, zvd_t, zvd_w, TAIL_S, DT)

        n = min(len(t_un_all), len(t_zv_all))
        t = t_un_all[:n]
        a_un = a_un_all[:n]
        a_zv = a_zv_all[:n]

        q_un, _, _ = sim_slosh(t, a_un, fn_nom, v["zeta"], t_move)
        q_zv, _, _ = sim_slosh(t, a_zv, fn_nom, v["zeta"], t_move + zvd_t[-1])
        traces[v["name"]] = (t, a_un, a_zv, q_un, q_zv)

        print(f"{v['name']} [{v['bucket']}]")
        print(f"  fn = {fn_nom:.3f} Hz | Td = {zvd_t[-1] * 1000:.1f} ms | weights = {[round(w, 4) for w in zvd_w]}")

        for pct in OFFSETS_PCT:
            fn_act = fn_nom * (1.0 + pct / 100.0)
            _, peak_un, res_un = sim_slosh(t, a_un, fn_act, v["zeta"], t_move)
            _, peak_zv, res_zv = sim_slosh(t, a_zv, fn_act, v["zeta"], t_move + zvd_t[-1])

            p_red = reduction_pct(peak_un, peak_zv)
            r_red = reduction_pct(res_un, res_zv)

            if pct in (-14, 0, 14):
                print(f"  {pct:+3d}% ({fn_act:.3f} Hz): peak red = {p_red:5.1f}% | resid red = {r_red:5.1f}%")

            sweep_rows.append({
                "case_name": v["name"],
                "payload_class": v["bucket"],
                "radius_mm": round(v["r"] * 1000.0, 1),
                "fill_height_mm": round(v["h"] * 1000.0, 1),
                "fn_nominal_hz": round(fn_nom, 4),
                "freq_offset_pct": pct,
                "fn_actual_hz": round(fn_act, 4),
                "peak_unshaped": round(peak_un, 6),
                "peak_zvd": round(peak_zv, 6),
                "peak_reduction_pct": round(p_red, 2),
                "resid_unshaped": round(res_un, 6),
                "resid_zvd": round(res_zv, 6),
                "resid_reduction_pct": round(r_red, 2),
            })
        print()

    # Sweep h/R from 0.15 to 2.00 for an R=40 mm cylinder
    mode_rows = []
    r_ref = 0.040
    for step in range(3, 41):
        ratio = round(step * 0.05, 2)
        h_m = ratio * r_ref
        fn = slosh_freq_hz(r_ref, h_m)
        imp_t, imp_w = zvd_shaper(fn, zeta=0.010)
        mode_rows.append({
            "radius_mm": 40.0,
            "fill_height_mm": round(h_m * 1000.0, 2),
            "h_over_R": ratio,
            "fn_hz": round(fn, 4),
            "t2_s": round(imp_t[1], 4),
            "zvd_duration_s": round(imp_t[2], 4),
            "a1": round(imp_w[0], 4),
            "a2": round(imp_w[1], 4),
            "a3": round(imp_w[2], 4),
        })

    save_csv(base_dir / "results" / "zvd_sweep_results.csv", sweep_rows)
    save_csv(base_dir / "results" / "vessel_modes_table.csv", mode_rows)
    print("Wrote CSVs to simulation/results/")

    if PLOT_ENABLED:
        save_plots(sweep_rows, traces, mode_rows, base_dir / "figures")
        print("Wrote PNGs to simulation/figures/")
    else:
        print("matplotlib not installed; skipped PNG plots.")


if __name__ == "__main__":
    main()
