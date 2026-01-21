import streamlit as st
import pandas as pd
import altair as alt
import seaborn as sns
import matplotlib.pyplot as plt

# --- 1. SETUP & CONFIGURATION ---
st.set_page_config(layout="wide", page_title="World Happiness Dashboard")

# --- 2. DATA LOADING ---
@st.cache_data
def load_data():
    df = pd.read_csv('happiness_clean.csv')
    try:
        df_2015 = pd.read_csv('2015.csv') 
        if 'Region' in df_2015.columns:
            region_map = dict(zip(df_2015['Country'], df_2015['Region']))
        else:
            region_map = {} 
        df['Region'] = df['Country'].map(region_map)
        df['Region'] = df['Region'].fillna('Other')
    except FileNotFoundError:
        df['Region'] = 'Unknown'
    return df

try:
    df = load_data()
except:
    st.error("Data file not found. Please export your 'df' to 'happiness_clean.csv' first.")
    st.stop()

# --- 3. SIDEBAR (Global Interaction) ---
st.sidebar.header("Global Filters")
selected_year = st.sidebar.slider("Select Year", 
                                  int(df['Year'].min()), 
                                  int(df['Year'].max()), 
                                  2019)

# FEATURE 1: Find My Country (Highlighting)
st.sidebar.divider()
st.sidebar.header("🔍 Find My Country")
all_countries = sorted(df['Country'].unique())
selected_countries = st.sidebar.multiselect("Highlight Countries", all_countries)

# FEATURE 2: Dynamic Scatter Plot Axes
st.sidebar.divider()
st.sidebar.header("📊 Chart Settings")

# Dictionary to map friendly labels to column names
axis_options = {
    'Economy (GDP)': 'GDP_per_Capita',
    'Social Support': 'Social_Support',
    'Health (Life Expectancy)': 'Life_Expectancy',
    'Freedom': 'Freedom',
    'Generosity': 'Generosity',
    'Trust (Corruption)': 'Corruption'
}

# X-Axis Selector
x_axis_label = st.sidebar.selectbox("Scatter Plot X-Axis", list(axis_options.keys()), index=0)
x_axis_col = axis_options[x_axis_label]

# Histogram Selector
dist_label = st.sidebar.selectbox("Histogram Variable", list(axis_options.keys()), index=2)
dist_col = axis_options[dist_label]


# --- 4. DATA PREPARATION (Current & Previous Year) ---
df_year = df[df['Year'] == selected_year].copy()
df_prev = df[df['Year'] == (selected_year - 1)]

# Helper to calculate delta
def get_delta(column):
    if df_prev.empty:
        return None # No previous year (e.g. 2015)
    return df_year[column].mean() - df_prev[column].mean()

# --- 5. MAIN HEADER & METRICS (FEATURE 4: DELTAS) ---
st.title(f"🌍 World Happiness Report: {selected_year} Overview")
st.markdown(f"Comparing **Happiness** against **{x_axis_label}**. Highlighted: {', '.join(selected_countries) if selected_countries else 'None'}")

col1, col2, col3 = st.columns(3)

# Metric 1: Avg Happiness
delta_score = get_delta('Score')
col1.metric("Avg Happiness Score", 
            f"{df_year['Score'].mean():.2f}", 
            f"{delta_score:+.2f}" if delta_score is not None else None)

# Metric 2: Avg GDP (or whatever is selected on X-axis)
delta_x = get_delta(x_axis_col)
col2.metric(f"Avg {x_axis_label}", 
            f"{df_year[x_axis_col].mean():.2f}", 
            f"{delta_x:+.2f}" if delta_x is not None else None)

# Metric 3: Happiest Country (No delta needed)
happiest = df_year.loc[df_year['Score'].idxmax()]['Country']
col3.metric("Happiest Country", happiest)

st.divider()

# --- 6. DEFINE ALTAIR CHARTS ---
brush = alt.selection_interval()

# FEATURE 1 Implementation: Conditional Sizing & Stroke
# If a country is in the 'selected_countries' list, make it BIGGER and give it a black border.
# We create a boolean column for Altair to use
df_year['Is_Selected'] = df_year['Country'].isin(selected_countries)

# Viz 1: Scatter Plot (Dynamic Axes + Highlight)
scatter = alt.Chart(df_year).mark_circle().encode(
    x=alt.X(x_axis_col, title=x_axis_label),  # Dynamic X-Axis
    y=alt.Y('Score', title='Happiness Score'),
    
    # Color: Gray out unselected points (Brush), otherwise color by Region
    color=alt.condition(
        brush, 
        alt.Color('Region', scale=alt.Scale(scheme='tableau10')), 
        alt.value('lightgray'), 
        legend=None
    ),
    
    # Size: If "Is_Selected" is True, make it huge (200), otherwise normal (60)
    size=alt.condition(
        alt.datum.Is_Selected, 
        alt.value(300),  # Highlight size
        alt.value(60)    # Normal size
    ),
    
    # Stroke: Add a black border to selected countries
    stroke=alt.condition(
        alt.datum.Is_Selected,
        alt.value('black'),
        alt.value('transparent')
    ),
    
    strokeWidth=alt.condition(
        alt.datum.Is_Selected,
        alt.value(2),
        alt.value(0)
    ),
    
    tooltip=['Country', 'Score', x_axis_col, 'Region']
).add_params(brush).properties(
    title=f"{x_axis_label} vs. Happiness",
    height=400
)

# Viz 2: Bar Chart (Unchanged logic, just listens to brush)
bars = alt.Chart(df_year).mark_bar().encode(
    x=alt.X('count()', title='Count'),
    y=alt.Y('Region', sort='-x'),
    color='Region'
).transform_filter(brush).properties(
    title="Region Distribution",
    height=400
)

# Viz 3: Histogram (Dynamic Variable)
hist = alt.Chart(df_year).mark_bar().encode(
    x=alt.X(dist_col, bin=True, title=dist_label),
    y='count()',
    color=alt.value('teal')
).transform_filter(brush).properties(
    title=f"Distribution of {dist_label}",
    height=200
)

# Combine Charts
dashboard = (scatter | bars) & hist

# --- 7. SPLIT LAYOUT ---
col_main, col_side = st.columns([2, 1], gap="large")

with col_main:
    st.subheader("Interactive Data Explorer")
    st.altair_chart(dashboard, use_container_width=True)

with col_side:
    st.subheader("Correlations Heat Map")
    st.markdown("""
    **Insight:** Even across different years, **GDP** and **Life Expectancy** remain the strongest predictors of happiness.
    """)
    
    fig, ax = plt.subplots(figsize=(5, 5))
    corr_cols = ['Score', 'GDP_per_Capita', 'Social_Support', 'Life_Expectancy', 'Freedom', 'Generosity']
    corr = df_year[corr_cols].corr()
    
    sns.heatmap(corr, annot=True, cmap='cividis', ax=ax, cbar=False, fmt=".2f")
    st.pyplot(fig)
