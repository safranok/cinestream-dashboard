import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.express as px
from datetime import date

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="🎬 CineStream Analytics Dashboard",
    layout="wide"
)

# -----------------------------
# LOAD & CLEAN DATA
# -----------------------------
@st.cache_data
def load_data():

    df = pd.read_csv("data/CineStream_Catalog.csv")

    # Remove duplicates
    df = df.drop_duplicates()

    # Clean text columns
    text_cols = [
        "Type",
        "Genre",
        "Language",
        "Country",
        "Director",
        "AgeRating",
        "TrendingStatus"
    ]

    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()

    df["Type"] = df["Type"].str.title()

    # Convert date
    df["AddedDate"] = pd.to_datetime(
        df["AddedDate"],
        errors="coerce"
    )

    # Invalid ratings
    df.loc[
        (df["IMDbScore"] < 1) |
        (df["IMDbScore"] > 10),
        "IMDbScore"
    ] = np.nan

    df.loc[
        (df["CriticRating"] < 1) |
        (df["CriticRating"] > 10),
        "CriticRating"
    ] = np.nan

    # Runtime outlier
    df.loc[
        df["RuntimeMinutes"] > 1000,
        "RuntimeMinutes"
    ] = np.nan

    # Negative subscribers
    df.loc[
        df["SubscribersGainedThousands"] < 0,
        "SubscribersGainedThousands"
    ] = 0

    # Derived columns
    df["Profit_Cr"] = (
        df["RevenueCr"] -
        df["ProductionCostCr"]
    )

    df["ROI_Pct"] = (
        df["Profit_Cr"] /
        df["ProductionCostCr"]
    ) * 100

    df["Performance_Band"] = np.where(
        df["Profit_Cr"] > 20,
        "Hit",
        np.where(
            df["Profit_Cr"] >= 0,
            "Break-even",
            "Flop"
        )
    )
    df.to_csv(
        r"C:\Users\safra\Downloads\CineStream\outputs\cleaned_cinestream.csv",
        index=False
    )


    return df


df = load_data()

# -----------------------------
# HEADER
# -----------------------------
st.title("🎬 CineStream Content Analytics Dashboard")

st.caption(
    "Interactive dashboard for analyzing OTT content performance."
)

st.markdown("---")

# -----------------------------
# SIDEBAR FILTERS
# -----------------------------
with st.sidebar:

    st.header("Filters")

    st.caption(
        "Change filters and click Apply."
    )

    with st.form("filters_form"):

        genre = st.multiselect(
            "Genre",
            sorted(df["Genre"].dropna().unique())
        )

        language = st.multiselect(
            "Language",
            sorted(df["Language"].dropna().unique())
        )

        age = st.multiselect(
            "Age Rating",
            sorted(df["AgeRating"].dropna().unique())
        )

        content_type = st.selectbox(
            "Type",
            ["All"] +
            sorted(df["Type"].dropna().unique())
        )

        imdb_range = st.slider(
            "IMDb Score",
            1.0,
            10.0,
            (1.0, 10.0)
        )

        runtime_range = st.slider(
            "Runtime Minutes",
            int(df["RuntimeMinutes"].min()),
            int(df["RuntimeMinutes"].max()),
            (
                int(df["RuntimeMinutes"].min()),
                int(df["RuntimeMinutes"].max())
            )
        )

        min_date = df["AddedDate"].min().date()
        max_date = df["AddedDate"].max().date()

        date_range = st.date_input(
            "Added Date Range",
            value=(min_date, max_date)
        )

        chart_color = st.color_picker(
            "Chart Color",
            "#1f77b4"
        )

        apply = st.form_submit_button(
            "Apply Filters"
        )

# -----------------------------
# FILTER DATA
# -----------------------------
filtered = df.copy()

if genre:
    filtered = filtered[
        filtered["Genre"].isin(genre)
    ]

if language:
    filtered = filtered[
        filtered["Language"].isin(language)
    ]

if age:
    filtered = filtered[
        filtered["AgeRating"].isin(age)
    ]

if content_type != "All":
    filtered = filtered[
        filtered["Type"] == content_type
    ]

filtered = filtered[
    filtered["IMDbScore"].between(
        imdb_range[0],
        imdb_range[1]
    )
]

filtered = filtered[
    filtered["RuntimeMinutes"].between(
        runtime_range[0],
        runtime_range[1]
    )
]

if len(date_range) == 2:
    filtered = filtered[
        filtered["AddedDate"].between(
            pd.to_datetime(date_range[0]),
            pd.to_datetime(date_range[1])
        )
    ]

# -----------------------------
# EMPTY STATE
# -----------------------------
if filtered.empty:
    st.warning(
        "No titles match current filters. "
        "Try loosening filter conditions."
    )
    st.stop()

# -----------------------------
# KPI SECTION
# -----------------------------
with st.container():

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Total Titles",
        len(filtered)
    )

    c2.metric(
        "Views (Millions)",
        f"{filtered['ViewsMillions'].sum():,.1f}"
    )

    c3.metric(
        "Watch Hours (Millions)",
        f"{filtered['WatchHoursMillions'].sum():,.1f}"
    )

    c4.metric(
        "Average IMDb",
        f"{filtered['IMDbScore'].mean():.2f}"
    )

st.markdown("---")

# -----------------------------
# DOWNLOAD BUTTON
# -----------------------------
st.download_button(
    "Download Filtered Catalog CSV",
    filtered.to_csv(index=False),
    file_name=f"cinestream_{date.today()}.csv",
    mime="text/csv"
)

# -----------------------------
# TABS
# -----------------------------
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Overview",
        "Genres & Languages",
        "Money",
        "Quality Alerts"
    ]
)

# =============================
# OVERVIEW TAB
# =============================
with tab1:

    col1, col2 = st.columns(2)

    with col1:

        monthly = (
            filtered
            .groupby(
                filtered["AddedDate"]
                .dt.to_period("M")
            )
            .size()
        )

        st.subheader("Titles Added Per Month")
        st.line_chart(monthly)

    with col2:

        type_count = (
            filtered["Type"]
            .value_counts()
        )

        st.subheader("Titles By Type")
        st.bar_chart(type_count)

    st.subheader("Catalog Sample")
    st.dataframe(
        filtered.head(10),
        use_container_width=True
    )

# =============================
# GENRES TAB
# =============================
with tab2:

    left, right = st.columns(2)

    with left:

        genre_views = (
            filtered
            .groupby("Genre")
            ["ViewsMillions"]
            .sum()
            .nlargest(10)
            .sort_values()
        )

        fig, ax = plt.subplots(
            figsize=(8, 5)
        )

        ax.barh(
            genre_views.index,
            genre_views.values,
            color=chart_color
        )

        ax.set_title(
            "Top Genres by Views"
        )

        ax.set_xlabel(
            "Views (Millions)"
        )

        st.pyplot(fig)

    with right:

        treemap = px.treemap(
            filtered,
            path=[
                "Language",
                "Genre"
            ],
            values="ViewsMillions",
            title="Language → Genre Treemap"
        )

        st.plotly_chart(
            treemap,
            use_container_width=True
        )

    lang_perf = (
        filtered
        .groupby("Language")
        ["ViewsMillions"]
        .mean()
    )

    best_lang = lang_perf.idxmax()
    worst_lang = lang_perf.idxmin()

    st.success(
        f"Best Language: {best_lang}"
    )

    st.warning(
        f"Worst Language: {worst_lang}"
    )

# =============================
# MONEY TAB
# =============================
with tab3:

    avg_roi = filtered["ROI_Pct"].mean()

    if avg_roi >= 0:
        st.info(
            f"Average ROI = {avg_roi:.2f}%"
        )
    else:
        st.error(
            f"Average ROI = {avg_roi:.2f}%"
        )

    col1, col2 = st.columns(2)

    with col1:

        scatter = px.scatter(
            filtered,
            x="ProductionCostCr",
            y="RevenueCr",
            color="Performance_Band",
            hover_name="Title",
            title="Cost vs Revenue"
        )

        st.plotly_chart(
            scatter,
            use_container_width=True
        )

    with col2:

        roi_genre = (
            filtered
            .groupby("Genre")
            ["ROI_Pct"]
            .mean()
            .sort_values()
        )

        fig, ax = plt.subplots(
            figsize=(8, 5)
        )

        ax.bar(
            roi_genre.index,
            roi_genre.values
        )

        ax.set_title(
            "Average ROI by Genre"
        )

        ax.tick_params(
            axis="x",
            rotation=45
        )

        st.pyplot(fig)

# =============================
# QUALITY TAB
# =============================
with tab4:

    loss_titles = (
        filtered["Profit_Cr"] < 0
    ).sum()

    if loss_titles == 0:
        st.success(
            "No loss-making titles."
        )

    elif loss_titles <= 5:
        st.warning(
            f"{loss_titles} loss-making titles."
        )

    else:
        st.error(
            f"{loss_titles} loss-making titles."
        )

    col1, col2 = st.columns(2)

    with col1:

        fig, ax = plt.subplots()

        ax.hist(
            filtered["IMDbScore"]
            .dropna(),
            bins=15
        )

        ax.axvline(
            filtered["IMDbScore"]
            .mean(),
            linestyle="--",
            color="red"
        )

        ax.set_title(
            "IMDb Distribution"
        )

        st.pyplot(fig)

    with col2:

        fig, ax = plt.subplots()

        ax.scatter(
            filtered["IMDbScore"],
            filtered["ViewsMillions"]
        )

        ax.set_title(
            "IMDb vs Views"
        )

        ax.set_xlabel(
            "IMDb Score"
        )

        ax.set_ylabel(
            "Views (Millions)"
        )

        st.pyplot(fig)

# -----------------------------
# EXPANDER
# -----------------------------
with st.expander(
    "How this dashboard works"
):

    st.markdown(
        """
        **Overview**  
        General platform statistics.

        **Genres & Languages**  
        Analyze audience preferences.

        **Money**  
        Revenue, cost, ROI and profitability.

        **Quality Alerts**  
        Ratings, views and risky titles.
        """
    )
    