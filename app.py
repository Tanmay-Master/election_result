import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from fpdf import FPDF
import tempfile
import os

# -----------------------------------------------------------------------------
# 1. Page Configuration & Data Loading
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Election Intelligence 2025", layout="wide")

st.title("🗳️ Election Intelligence & Margin Analysis Dashboard")

@st.cache_data
def load_data():
    try:
        df = pd.read_csv("election.csv")
        df.columns = df.columns.str.strip()
        df['Votes'] = pd.to_numeric(df['Votes'], errors='coerce').fillna(0).astype(int)
        df['Prabhag'] = df['Prabhag'].astype(str).str.strip()
        df['Party'] = df['Party'].fillna('Independent').str.strip()
        df['Election_type'] = df['Election_type'].str.strip()
        return df
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return pd.DataFrame()

df = load_data()
if df.empty: st.stop()

# --- Global Color Mapping ---
PARTY_COLORS = {
    "BJP": "Blue",
    "SS": "Orange",
    "SS-UBT": "violet",
    "Independent": "gray",
    "Nota": "black"
}

# -----------------------------------------------------------------------------
# 2. PDF Class
# -----------------------------------------------------------------------------
class PDF_Report(FPDF):
    def __init__(self, watermark=""):
        super().__init__()
        self.watermark = watermark
    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()} | {self.watermark}', 0, 0, 'C')

# -----------------------------------------------------------------------------
# 3. Sidebar Configuration
# -----------------------------------------------------------------------------
st.sidebar.header("📁 PDF Export Filters")
def natural_sort_key(s): return int(s) if s.isdigit() else s

unique_prabhags = sorted(df['Prabhag'].unique(), key=natural_sort_key)
unique_parties = sorted(df['Party'].unique())

selected_pdf_prabhags = st.sidebar.multiselect("Select Prabhags for PDF:", unique_prabhags, default=unique_prabhags)
selected_pdf_parties = st.sidebar.multiselect("Select Parties for PDF:", unique_parties, default=unique_parties)

# -----------------------------------------------------------------------------
# 4. Analytics Logic
# -----------------------------------------------------------------------------
def get_margin_analysis(data):
    agg = data.groupby(['Prabhag', 'Election_type', 'Name', 'Party'])['Votes'].sum().reset_index()
    sorted_agg = agg.sort_values(['Prabhag', 'Election_type', 'Votes'], ascending=[True, True, False])
    
    winners = sorted_agg.groupby(['Prabhag', 'Election_type']).head(1).copy()
    runners = sorted_agg.groupby(['Prabhag', 'Election_type']).nth(1).reset_index()
    
    margin_df = pd.merge(winners, runners[['Prabhag', 'Election_type', 'Votes', 'Party', 'Name']], 
                         on=['Prabhag', 'Election_type'], suffixes=('_W', '_R'))
    margin_df['Margin'] = margin_df['Votes_W'] - margin_df['Votes_R']
    return margin_df

# -----------------------------------------------------------------------------
# 5. App Tabs
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Prabhag Dashboard", 
    "🎯 Margin Comparison", 
    "📈 City Insights",
    "🔢 Data Tables", 
    "🖨️ Export Center"
])

# --- TAB 1: PRABHAG DASHBOARD ---
with tab1:
    selected_p = st.selectbox("Detailed Analysis for Prabhag:", unique_prabhags)
    dash_df = df[df['Prabhag'] == selected_p]
    
    chart_data = dash_df.groupby(['Name', 'Party', 'Election_type'])['Votes'].sum().reset_index()
    fig = px.bar(chart_data, x='Name', y='Votes', color='Party', facet_col='Election_type', text='Votes', 
                 title=f"Vote Distribution - Prabhag {selected_p}", color_discrete_map=PARTY_COLORS)
    fig.update_xaxes(matches=None, type='category')
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

# --- TAB 2: MARGIN COMPARISON ---
with tab2:
    st.header("Victory Margin Analysis (Winner vs Runner-up)")
    margin_df = get_margin_analysis(df)
    
    etypes = sorted(margin_df['Election_type'].unique())
    selected_etype = st.selectbox("Filter Margin by Election Type:", ["All"] + etypes)
    
    plot_margin_df = margin_df if selected_etype == "All" else margin_df[margin_df['Election_type'] == selected_etype]
    
    fig_margin = px.bar(plot_margin_df.sort_values('Margin'), x='Prabhag', y='Margin', color='Party_W', 
                        facet_row='Election_type' if selected_etype == "All" else None, 
                        text='Margin', hover_data=['Name_W', 'Name_R'],
                        title="Victory Margins by Category", color_discrete_map=PARTY_COLORS, height=600)
    fig_margin.update_xaxes(type='category', categoryorder='category ascending')
    st.plotly_chart(fig_margin, use_container_width=True)
    
    st.subheader("Detailed Margin Table")
    st.dataframe(plot_margin_df[['Prabhag', 'Election_type', 'Name_W', 'Party_W', 'Name_R', 'Party_R', 'Margin']], use_container_width=True)

# --- TAB 3: CITY INSIGHTS ---
with tab3:
    st.header("City Performance Metrics")
    winners_agg = get_margin_analysis(df) 
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Total Seats Won by Party")
        fig_pie = px.pie(winners_agg, values='Votes_W', names='Party_W', hole=0.4, color_discrete_map=PARTY_COLORS)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with c2:
        st.subheader("Party Strike Rate")
        # FIX: Ensure Party is a column, not an index
        total_cand = df.groupby('Party')['Name'].nunique().reset_index(name='Candidates')
        total_wins = winners_agg.groupby('Party_W').size().reset_index(name='Wins')
        
        strike_rate_df = pd.merge(total_cand, total_wins, left_on='Party', right_on='Party_W', how='left').fillna(0)
        strike_rate_df['Rate'] = (strike_rate_df['Wins'] / strike_rate_df['Candidates']) * 100
        
        fig_strike = px.bar(strike_rate_df, x='Party', y='Rate', color='Party', 
                            text=strike_rate_df['Rate'].apply(lambda x: f'{x:.1f}%'),
                            color_discrete_map=PARTY_COLORS, title="Efficiency: Wins vs Contested")
        st.plotly_chart(fig_strike, use_container_width=True)

# --- TAB 4: DATA TABLES ---
with tab4:
    st.header("Consolidated Results Table")
    table_df = df.groupby(['Prabhag', 'Election_type', 'Party', 'Name'])['Votes'].sum().reset_index()
    # Numeric sorting for table
    table_df['P_Sort'] = pd.to_numeric(table_df['Prabhag'], errors='coerce')
    table_df = table_df.sort_values(['P_Sort', 'Votes'], ascending=[True, False]).drop(columns=['P_Sort'])
    st.dataframe(table_df, use_container_width=True)

# --- TAB 5: EXPORT CENTER ---
with tab5:
    st.header("Download Official Reports")
    watermark = st.text_input("Report Footer Text:", value="Election Analysis 2025")
    
    col_pdf1, col_pdf2 = st.columns(2)
    
    with col_pdf1:
        st.subheader("1. Full Result PDF")
        if st.button("🚀 Generate Full Result PDF"):
            pdf = PDF_Report(watermark=watermark)
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # Apply Filters
            f_df = df[(df['Prabhag'].isin(selected_pdf_prabhags)) & (df['Party'].isin(selected_pdf_parties))]
            report_prabhags = sorted(f_df['Prabhag'].unique(), key=natural_sort_key)

            for prabhag in report_prabhags:
                pdf.add_page()
                pdf.set_font("Helvetica", 'B', 16)
                pdf.cell(200, 10, txt=f"Result: Prabhag {prabhag}", ln=True, align='C')
                
                p_df = f_df[f_df['Prabhag'] == prabhag]
                chart_data = p_df.groupby(['Name', 'Party'])['Votes'].sum().reset_index()
                fig = px.bar(chart_data, x='Name', y='Votes', color='Party', text='Votes', template="plotly_white",
                             title=f"Prabhag {prabhag} Summary", color_discrete_map=PARTY_COLORS)
                fig.update_xaxes(type='category')
                
                img_bytes = fig.to_image(format="png", engine="kaleido")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(img_bytes)
                    pdf.image(tmp.name, x=10, y=35, w=190)
            st.download_button("📥 Download Result PDF", data=bytes(pdf.output()), file_name="Election_Results_2025.pdf")

    with col_pdf2:
        st.subheader("2. Margin Analysis PDF")
        if st.button("🎯 Generate Margin Report PDF"):
            pdf_m = PDF_Report(watermark=watermark)
            pdf_m.set_auto_page_break(auto=True, margin=15)
            
            m_report_df = get_margin_analysis(df)
            m_report_df = m_report_df[m_report_df['Prabhag'].isin(selected_pdf_prabhags)]
            
            for etype in sorted(m_report_df['Election_type'].unique()):
                pdf_m.add_page()
                pdf_m.set_font("Helvetica", 'B', 16)
                pdf_m.cell(200, 10, txt=f"Margin Report: {etype}", ln=True, align='C')
                
                type_df = m_report_df[m_report_df['Election_type'] == etype]
                fig_m = px.bar(type_df.sort_values('Margin'), x='Prabhag', y='Margin', color='Party_W', 
                               text='Margin', title=f"Margins for {etype}", color_discrete_map=PARTY_COLORS)
                fig_m.update_xaxes(type='category')
                
                img_bytes_m = fig_m.to_image(format="png", engine="kaleido")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(img_bytes_m)
                    pdf_m.image(tmp.name, x=10, y=35, w=190)
            st.download_button("📥 Download Margin PDF", data=bytes(pdf_m.output()), file_name="Margin_Analysis_2025.pdf")
