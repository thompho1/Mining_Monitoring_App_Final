
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from theme import page_header

from data import ensure_sample_data, load_workers, update_worker_risk
from monitoring import classify_risk
from ui import flash, show_flash

LEVELS = ["Low", "Medium", "High", "Critical"]
LEVEL_COLOURS = ["#9fd3a8", "#f4d35e", "#f08c3a", "#d64545"]
LIKELIHOOD_LABELS = {1: "Rare", 2: "Unlikely", 3: "Possible", 4: "Likely", 5: "Almost certain"}
CONSEQUENCE_LABELS = {1: "Insignificant", 2: "Minor", 3: "Moderate", 4: "Major", 5: "Catastrophic"}


def risk_message(score: int, level: str) -> tuple[str, str] | None:
    """Return (kind, text) for the warning shown when a high or critical risk is identified."""
    if level == "Critical":
        return "error", f"CRITICAL RISK (score {score}): stop the activity and apply immediate controls."
    if level == "High":
        return "warning", f"HIGH RISK (score {score}): urgent management attention and risk reduction required."
    return None


def _show_message(score: int, level: str) -> None:
    message = risk_message(score, level)
    if message is None:
        st.success(f"{level} risk (score {score}): manage with routine procedures.")
    elif message[0] == "error":
        st.error(message[1])
    else:
        st.warning(message[1])


def _matrix(likelihood: int, consequence: int) -> go.Figure:
    level_index = {name: i for i, name in enumerate(LEVELS)}
    z, text = [], []
    for l in range(1, 6):
        z_row, t_row = [], []
        for c in range(1, 6):
            score, level = classify_risk(l, c)
            z_row.append(level_index[level])
            t_row.append(f"{score}<br>{level}")
        z.append(z_row)
        text.append(t_row)
    scale = []
    for i, colour in enumerate(LEVEL_COLOURS):
        scale += [[i / 4, colour], [(i + 1) / 4, colour]]
    fig = go.Figure(go.Heatmap(z=z, x=list(range(1, 6)), y=list(range(1, 6)), text=text,
                               texttemplate="%{text}", colorscale=scale, zmin=0, zmax=3,
                               showscale=False, hoverinfo="skip", xgap=3, ygap=3))
    fig.add_trace(go.Scatter(x=[consequence], y=[likelihood], mode="markers", hoverinfo="skip",
                             marker=dict(symbol="square-open", size=62, line=dict(width=4, color="#111"))))
    fig.update_layout(title="Risk matrix (selected cell outlined)", showlegend=False, height=430,
                      xaxis=dict(title="Consequence", tickmode="array", tickvals=list(range(1, 6)),
                                 ticktext=[f"{k} {v}" for k, v in CONSEQUENCE_LABELS.items()]),
                      yaxis=dict(title="Likelihood", tickmode="array", tickvals=list(range(1, 6)),
                                 ticktext=[f"{k} {v}" for k, v in LIKELIHOOD_LABELS.items()]))
    return fig


def _calculator_tab() -> None:
    left, right = st.columns([1, 2])
    with left:
        likelihood = st.slider("Likelihood (1-5)", 1, 5, 3)
        consequence = st.slider("Consequence (1-5)", 1, 5, 3)
        score, level = classify_risk(likelihood, consequence)
        st.metric("Risk score", score)
        st.write(f"Classification: **{level}**")
        _show_message(score, level)
        st.caption("Scores 1-4 are Low, 5-9 Medium, 10-16 High and 17-25 Critical.")
    right.plotly_chart(_matrix(likelihood, consequence))


def _register_tab(workers: pd.DataFrame) -> None:
    summary = workers.groupby("department").agg(
        workers=("worker_id", "count"),
        average_score=("risk_score", "mean"),
        high_or_critical=("risk_level", lambda s: int(s.isin(["High", "Critical"]).sum())),
    ).reset_index()
    summary["share_high_or_critical"] = summary["high_or_critical"] / summary["workers"] * 100
    summary = summary.sort_values("average_score", ascending=False)

    left, right = st.columns([1, 1])
    left.dataframe(summary, hide_index=True, column_config={
        "average_score": st.column_config.NumberColumn("average score", format="%.1f"),
        "high_or_critical": st.column_config.NumberColumn("high or critical"),
        "share_high_or_critical": st.column_config.NumberColumn("% high or critical", format="%.0f")})
    fig = px.bar(summary.sort_values("average_score"), x="average_score", y="department", orientation="h",
                 title="Average risk score by department", color_discrete_sequence=["#2a78d6"])
    fig.update_layout(yaxis_title=None, xaxis_title="Average risk score")
    right.plotly_chart(fig)

    levels = st.multiselect("Show risk levels", LEVELS, default=["High", "Critical"])
    shown = workers[workers["risk_level"].isin(levels)] if levels else workers
    st.dataframe(shown.sort_values("risk_score", ascending=False)[
        ["worker_id", "department", "job_role", "shift", "likelihood", "consequence", "risk_score", "risk_level"]],
        hide_index=True)


def _reassess_tab(workers: pd.DataFrame) -> None:
    worker_id = st.selectbox("Worker", workers["worker_id"].tolist(), key="risk_worker")
    row = workers[workers["worker_id"] == worker_id].iloc[0]
    st.write(f"Current assessment: likelihood {int(row['likelihood'])}, consequence {int(row['consequence'])}, "
             f"score {int(row['risk_score'])} ({row['risk_level']}).")
    with st.form("reassess"):
        c = st.columns(2)
        likelihood = c[0].slider("New likelihood (1-5)", 1, 5, int(row["likelihood"]), key=f"lik_{worker_id}")
        consequence = c[1].slider("New consequence (1-5)", 1, 5, int(row["consequence"]), key=f"con_{worker_id}")
        submitted = st.form_submit_button("Save assessment")
    if not submitted:
        return
    update_worker_risk(worker_id, likelihood, consequence)
    score, level = classify_risk(likelihood, consequence)
    messages = [("success", f"Assessment saved for {worker_id}: score {score} ({level}).")]
    warning = risk_message(score, level)
    if warning:
        messages.append(warning)
    flash(*messages)


def show_risk() -> None:
    ensure_sample_data()
    workers = load_workers()

    page_header("Risk Assessment")
    show_flash()
    calculator, register, reassess = st.tabs(["Risk calculator", "Worker risk register", "Reassess a worker"])
    with calculator:
        _calculator_tab()
    with register:
        _register_tab(workers)
    with reassess:
        _reassess_tab(workers)
