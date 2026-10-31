"""Plotly chart components styled for TRANSFERA Clean Light Football Intelligence Theme."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Clean Transfermarkt-inspired light chart layout
CHART_THEME = {
    "paper_bgcolor": "#FFFFFF",
    "plot_bgcolor": "#FFFFFF",
    "font": {"color": "#17212B", "family": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif"},
    "margin": {"l": 35, "r": 20, "t": 45, "b": 35},
}

# TRANSFERA light professional series palette
TRANSFERA_PALETTE = ["#02BFD0", "#3185C7", "#20A56B", "#E5A52B", "#66727D", "#8A959E", "#E05252"]


def render_league_bar_chart(league_df: pd.DataFrame, metric: str = "total_market_value") -> go.Figure:
    """Render League Market Value bar chart matching clean light aesthetic."""
    if len(league_df) == 0:
        fig = go.Figure()
        fig.update_layout(**CHART_THEME)
        return fig

    # Top 8 leagues
    df_plot = league_df.head(8).copy()

    # Cohesive aqua shades sequence
    aqua_shades = ["#02BFD0", "#00A9B9", "#20A56B", "#3185C7", "#5BA8D9", "#8CA7AD", "#B0BEC5", "#CFD8DC"]
    colors = aqua_shades[: len(df_plot)]

    # Determine metric and label
    if metric == "avg_market_value":
        y_vals = df_plot["avg_market_value"] / 1_000_000
        text_vals = [f"€{v:.1f}M" for v in y_vals]
        y_title = "Average Value (€ Millions)"
    elif metric == "median_market_value":
        y_vals = df_plot["median_market_value"] / 1_000_000
        text_vals = [f"€{v:.1f}M" for v in y_vals]
        y_title = "Median Value (€ Millions)"
    else:
        y_vals = df_plot["total_market_value"] / 1_000_000_000
        text_vals = [f"€{v:.1f}B" for v in y_vals]
        y_title = "Total Capital (€ Billions)"

    fig = go.Figure(
        data=[
            go.Bar(
                x=df_plot["league_name"],
                y=y_vals,
                text=text_vals,
                textposition="outside",
                marker_color=colors,
                marker_line=dict(color="#E2E6E9", width=1),
                hovertemplate="<b>%{x}</b><br>" + y_title + ": %{y:.2f}<br>Players: %{customdata:,}<extra></extra>",
                customdata=df_plot["player_count"],
            )
        ]
    )

    fig.update_layout(
        **CHART_THEME,
        title=dict(
            text="<b>Market Value by Competition</b>",
            font=dict(size=13, color="#17212B"),
            x=0.02,
            y=0.96,
        ),
        xaxis=dict(showgrid=False, tickfont=dict(size=11, color="#66727D")),
        yaxis=dict(
            showgrid=True,
            gridcolor="#EDF0F2",
            zeroline=True,
            zerolinecolor="#E2E6E9",
            title=dict(text=y_title, font=dict(size=11, color="#66727D")),
            tickfont=dict(size=10, color="#66727D"),
        ),
        height=320,
    )
    return fig


def render_country_map(country_df: pd.DataFrame) -> go.Figure:
    """Render geographic choropleth map with clean light theme."""
    if len(country_df) == 0:
        fig = go.Figure()
        fig.update_layout(**CHART_THEME)
        return fig

    df_plot = country_df.copy()
    df_plot["total_val_b"] = df_plot["total_market_value"] / 1_000_000_000

    fig = px.choropleth(
        df_plot,
        locations="country",
        locationmode="country names",
        color="total_val_b",
        hover_name="country",
        hover_data={"total_val_b": ":.2f", "player_count": ":,"},
        color_continuous_scale=[
            [0.0, "#E5F9FB"],
            [0.2, "#A8EEF5"],
            [0.5, "#02BFD0"],
            [0.8, "#008EA0"],
            [1.0, "#01606D"],
        ],
    )

    fig.update_geos(
        showcoastlines=True,
        coastlinecolor="#CBD2D7",
        showland=True,
        landcolor="#F4F5F6",
        showocean=True,
        oceancolor="#FFFFFF",
        showlakes=False,
        bgcolor="#FFFFFF",
        projection_type="natural earth",
    )

    fig.update_layout(
        **CHART_THEME,
        title=dict(
            text="<b>Market Capital by Nation</b>",
            font=dict(size=13, color="#17212B"),
            x=0.02,
            y=0.96,
        ),
        coloraxis_colorbar=dict(
            title=dict(text="€ Billions", font=dict(size=10, color="#66727D")),
            thickness=10,
            len=0.75,
            tickfont=dict(color="#66727D", size=9),
        ),
        height=320,
    )
    return fig


def render_position_donut(df: pd.DataFrame) -> go.Figure:
    """Render position-wise market value donut chart with clean light styling."""
    if len(df) == 0:
        fig = go.Figure()
        fig.update_layout(**CHART_THEME)
        return fig

    pos_agg = (
        df.groupby("position")
        .agg(total_val=("historical_market_value", "sum"), count=("player_id", "count"))
        .reset_index()
    )

    pos_colors = {
        "Attack": "#02BFD0",
        "Midfield": "#3185C7",
        "Defender": "#20A56B",
        "Goalkeeper": "#E5A52B",
        "Unknown": "#8A959E",
    }
    colors = [pos_colors.get(p, "#66727D") for p in pos_agg["position"]]
    total_val_b = df["historical_market_value"].sum() / 1_000_000_000

    fig = go.Figure(
        data=[
            go.Pie(
                labels=pos_agg["position"],
                values=pos_agg["total_val"],
                hole=0.68,
                marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
                textinfo="percent",
                hovertemplate="<b>%{label}</b><br>Capital: €%{value:,.0f}<br>Share: %{percent}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        **CHART_THEME,
        title=dict(
            text="<b>Position Distribution</b>",
            font=dict(size=13, color="#17212B"),
            x=0.02,
            y=0.96,
        ),
        showlegend=True,
        legend=dict(orientation="v", x=1.02, y=0.5, font=dict(size=11, color="#66727D")),
        height=280,
        annotations=[
            dict(
                text=f"<b>€{total_val_b:.1f}B</b><br><span style='font-size:10px; color:#8A959E;'>Total Value</span>",
                x=0.5,
                y=0.5,
                font_size=15,
                font_color="#17212B",
                showarrow=False,
            )
        ],
    )
    return fig


def render_age_histogram(df: pd.DataFrame) -> go.Figure:
    """Render Age distribution histogram in clean light theme."""
    if len(df) == 0:
        fig = go.Figure()
        fig.update_layout(**CHART_THEME)
        return fig

    valid_ages = df["age_at_reference_date"].dropna()
    valid_ages = valid_ages[(valid_ages >= 16) & (valid_ages <= 40)]

    age_counts = valid_ages.round().astype(int).value_counts().sort_index().reset_index()
    age_counts.columns = ["age", "count"]

    if len(age_counts) > 0:
        peak_row = age_counts.loc[age_counts["count"].idxmax()]
        peak_age = int(peak_row["age"])
        peak_cnt = int(peak_row["count"])
    else:
        peak_age, peak_cnt = 24, 0

    fig = px.bar(
        age_counts,
        x="age",
        y="count",
        color="age",
        color_continuous_scale=[[0, "#A8EEF5"], [0.5, "#02BFD0"], [1.0, "#017E8A"]],
    )

    fig.update_layout(
        **CHART_THEME,
        title=dict(
            text="<b>Age Distribution</b>",
            font=dict(size=13, color="#17212B"),
            x=0.02,
            y=0.96,
        ),
        xaxis=dict(
            title=dict(text="Age", font=dict(size=11, color="#66727D")),
            showgrid=False,
            dtick=2,
            tickfont=dict(size=10, color="#66727D"),
        ),
        yaxis=dict(
            title=dict(text="Players", font=dict(size=11, color="#66727D")),
            showgrid=True,
            gridcolor="#EDF0F2",
            zeroline=True,
            zerolinecolor="#E2E6E9",
            tickfont=dict(size=10, color="#66727D"),
        ),
        coloraxis_showscale=False,
        height=280,
        annotations=[
            dict(
                x=peak_age,
                y=peak_cnt,
                text=f"Peak: Age {peak_age} ({peak_cnt:,})",
                showarrow=True,
                arrowhead=2,
                arrowcolor="#02BFD0",
                arrowsize=1,
                arrowwidth=1.5,
                ax=0,
                ay=-26,
                font=dict(color="#17212B", size=10, weight="bold"),
                bgcolor="#FFFFFF",
                bordercolor="#02BFD0",
                borderwidth=1,
            )
        ]
        if peak_cnt > 0
        else [],
    )
    return fig


def render_performance_scatter(df: pd.DataFrame) -> go.Figure:
    """Render Goals+Assists/90 vs Market Value scatter plot with clean light palette."""
    if len(df) == 0:
        fig = go.Figure()
        fig.update_layout(**CHART_THEME)
        return fig

    sub = df[df["minutes_played"] >= 450].copy()
    if len(sub) == 0:
        sub = df.copy()

    sub["goal_contributions_p90"] = (sub["goals_per_90"] + sub["assists_per_90"]).round(2)
    sub["market_value_m"] = sub["historical_market_value"] / 1_000_000

    fig = px.scatter(
        sub,
        x="goal_contributions_p90",
        y="market_value_m",
        color="position",
        size="minutes_played",
        hover_name="name",
        hover_data={
            "goal_contributions_p90": ":.2f",
            "market_value_m": ":.1f",
            "current_club_name": True,
            "minutes_played": ":,",
        },
        color_discrete_map={
            "Attack": "#02BFD0",
            "Midfield": "#3185C7",
            "Defender": "#20A56B",
            "Goalkeeper": "#E5A52B",
        },
        log_y=True,
    )

    fig.update_layout(
        **CHART_THEME,
        title=dict(
            text="<b>Market Value vs Performance</b> (Log Scale)",
            font=dict(size=13, color="#17212B"),
            x=0.02,
            y=0.96,
        ),
        xaxis=dict(
            title=dict(text="Goals + Assists (per 90)", font=dict(size=11, color="#66727D")),
            showgrid=True,
            gridcolor="#EDF0F2",
            tickfont=dict(size=10, color="#66727D"),
        ),
        yaxis=dict(
            title=dict(text="Market Value (€M, Log)", font=dict(size=11, color="#66727D")),
            showgrid=True,
            gridcolor="#EDF0F2",
            tickfont=dict(size=10, color="#66727D"),
        ),
        legend=dict(orientation="h", y=1.12, x=0.5, xanchor="center", font=dict(size=10, color="#66727D")),
        height=280,
    )
    return fig


def render_player_radar(metrics_dict: dict[str, float], title: str = "Scouting Radar Profile") -> go.Figure:
    """Render player scouting radar chart in clean light palette."""
    categories = list(metrics_dict.keys())
    values = list(metrics_dict.values())

    categories_closed = categories + [categories[0]]
    values_closed = values + [values[0]]

    fig = go.Figure(
        data=[
            go.Scatterpolar(
                r=values_closed,
                theta=categories_closed,
                fill="toself",
                fillcolor="rgba(2, 191, 208, 0.18)",
                line=dict(color="#02BFD0", width=2.5),
                marker=dict(size=6, color="#00A9B9"),
            )
        ]
    )

    fig.update_layout(
        **CHART_THEME,
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], showticklabels=False, linecolor="#EDF0F2"),
            angularaxis=dict(linecolor="#E2E6E9", tickfont=dict(size=10, color="#66727D")),
            bgcolor="#F8F9FA",
        ),
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(size=13, color="#17212B"),
            x=0.02,
            y=0.96,
        ),
        height=320,
    )
    return fig


def render_historical_valuation_line(history_df: pd.DataFrame) -> go.Figure:
    """Render historical market value progression chart in clean light style."""
    if len(history_df) == 0:
        fig = go.Figure()
        fig.update_layout(**CHART_THEME)
        return fig

    df_plot = history_df.sort_values("season").copy()
    df_plot["val_m"] = df_plot["historical_market_value"] / 1_000_000

    fig = go.Figure(
        data=[
            go.Scatter(
                x=df_plot["season"].astype(str),
                y=df_plot["val_m"],
                mode="lines+markers",
                line=dict(color="#02BFD0", width=3, shape="spline"),
                marker=dict(size=8, color="#FFFFFF", line=dict(color="#02BFD0", width=2.5)),
                fill="tozeroy",
                fillcolor="rgba(2, 191, 208, 0.12)",
                hovertemplate="Season %{x}<br>Valuation: <b>€%{y:.1f}M</b><br>Club: %{customdata}<extra></extra>",
                customdata=df_plot["current_club_name"],
            )
        ]
    )

    fig.update_layout(
        **CHART_THEME,
        title=dict(
            text="<b>Historical Market Value Trend</b>",
            font=dict(size=13, color="#17212B"),
            x=0.02,
            y=0.96,
        ),
        xaxis=dict(
            title=dict(text="Season", font=dict(size=11, color="#66727D")),
            showgrid=False,
            tickfont=dict(size=10, color="#66727D"),
        ),
        yaxis=dict(
            title=dict(text="Market Value (€ Millions)", font=dict(size=11, color="#66727D")),
            showgrid=True,
            gridcolor="#EDF0F2",
            zeroline=True,
            zerolinecolor="#E2E6E9",
            tickfont=dict(size=10, color="#66727D"),
        ),
        height=280,
    )
    return fig
