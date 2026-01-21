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
                                  2015)

# --- NEW: Dropdown for Histogram Variable ---
st.sidebar.divider()
st.sidebar.header("Chart Settings")
dist_options = {
    'Economy (GDP)': 'GDP_per_Capita',
    'Social Support': 'Social_Support',
    'Health (Life Expectancy)': 'Life_Expectancy',
    'Freedom': 'Freedom'
}
# User selects the friendly name, we get the column name
selected_dist_label = st.sidebar.selectbox("Select Distribution Variable", list(dist_options.keys()))
selected_dist_col = dist_options[selected_dist_label]

df_year = df[df['Year'] == selected_year]

# --- 4. MAIN HEADER & METRICS ---
st.title(f"🌍 World Happiness Report: {selected_year} Overview")
st.markdown("Explore how Wealth, Health and Social Support correlate with Happiness. **Drag your mouse** on the Scatter Plot to filter the other charts!")

# METRICS ROW
col1, col2, col3 = st.columns(3)
col1.metric("Avg Happiness Score", f"{df_year['Score'].mean():.2f}")
col2.metric("Avg GDP (Economy)", f"{df_year['GDP_per_Capita'].mean():.2f}")
col3.metric("Happiest Country", df_year.loc[df_year['Score'].idxmax()]['Country'])

st.divider()

# --- 5. DEFINE ALTAIR CHARTS (PREPARATION) ---
brush = alt.selection_interval()

# Viz 1: Scatter Plot
scatter = alt.Chart(df_year).mark_circle(size=60).encode(
    x=alt.X('GDP_per_Capita', title='GDP per Capita'),
    y=alt.Y('Score', title='Happiness Score'),
    color=alt.condition(brush, 'Region', alt.value('lightgray'), legend=None),
    tooltip=['Country', 'Score', 'GDP_per_Capita', 'Social_Support']
).add_params(brush).properties(
    title="Wealth vs. Happiness (Drag to filter)",
    height=400
)

# Viz 2: Bar Chart
bars = alt.Chart(df_year).mark_bar().encode(
    x=alt.X('count()', title='Count'),
    y=alt.Y('Region', sort='-x'),
    color='Region'
).transform_filter(brush).properties(
    title="Region Distribution",
    height=400
)

# Viz 3: Histogram (UPDATED to use selected_dist_col)
hist = alt.Chart(df_year).mark_bar().encode(
    x=alt.X(selected_dist_col, bin=True, title=selected_dist_label),
    y='count()',
    color=alt.value('teal')
).transform_filter(brush).properties(
    title=f"Distribution of {selected_dist_label}", # Dynamic Title
    height=200
)

# Combine Altair Charts
dashboard = (scatter | bars) & hist

# --- 6. SPLIT LAYOUT (MAIN DASHBOARD vs ANALYSIS) ---
col_main, col_side = st.columns([2, 1], gap="large")

with col_main:
    st.subheader("Interactive Data Explorer")
    st.altair_chart(dashboard, use_container_width=True)

with col_side:
    st.subheader("Correlations Heat Map")
    
    st.markdown("""
    **Insight:** Even across different years, **GDP** and **Life Expectancy** remain the strongest predictors of happiness.
    """)
    
    # Correlation Heatmap
    fig, ax = plt.subplots(figsize=(5, 5)) 
    
    # Select only numeric columns of interest
    corr_cols = ['Score', 'GDP_per_Capita', 'Social_Support', 'Life_Expectancy', 'Freedom']
    corr = df_year[corr_cols].corr()
    
    sns.heatmap(corr, annot=True, cmap='coolwarm', ax=ax, cbar=False, fmt=".2f")
    st.pyplot(fig)
