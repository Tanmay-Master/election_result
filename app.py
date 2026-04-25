import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    
    # --- ENHANCED SUNBURST ANALYSIS ---
    st.header("🌅 Enhanced Sunburst Analysis - Election Performance")
    
    # Advanced filtering options
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        available_elections = sorted(df['Election_type'].unique())
        selected_election = st.selectbox("Select Election Type:", available_elections, index=0)
    
    with col_filter2:
        available_rounds = sorted(df['Round'].unique())
        selected_rounds = st.multiselect("Select Rounds:", available_rounds, default=available_rounds)
    
    with col_filter3:
        available_parties = sorted(df['Party'].dropna().unique())
        selected_parties = st.multiselect("Filter by Parties:", available_parties, default=available_parties)
    
    # Apply filters
    filtered_df = df[
        (df['Election_type'] == selected_election) & 
        (df['Round'].isin(selected_rounds)) &
        (df['Party'].isin(selected_parties))
    ].copy()
    
    # Special handling for Nagar Sevak elections - Party-wise side-by-side comparison
    if selected_election in ['Nagarsevak A', 'Nagarsevak B'] and not filtered_df.empty:
        st.header(f"🏛️ {selected_election} - Party-wise Side-by-Side Analysis")
        
        # Remove rows with zero or null votes
        filtered_df = filtered_df[filtered_df['Votes'] > 0]
        
        # Get unique parties for side-by-side comparison
        parties_in_data = sorted(filtered_df['Party'].unique())
        
        # Create columns for each party
        party_cols = st.columns(len(parties_in_data))
        
        for idx, party in enumerate(parties_in_data):
            with party_cols[idx]:
                st.subheader(f"{party}")
                
                # Filter data for this specific party
                party_data = filtered_df[filtered_df['Party'] == party]
                
                if not party_data.empty:
                    # Create sunburst for this party
                    party_sunburst_data = party_data.groupby(['Name', 'Prabhag'])['Votes'].sum().reset_index()
                    
                    fig_party = px.sunburst(
                        party_sunburst_data,
                        path=['Name', 'Prabhag'],
                        values='Votes',
                        color_discrete_sequence=[PARTY_COLORS.get(party, 'gray')],
                        title=f"{party} Candidates"
                    )
                    
                    fig_party.update_traces(
                        textinfo="label+value",
                        hovertemplate='<b>%{label}</b><br>Votes: %{value:,}<br>% of Parent: %{percentParent}<extra></extra>'
                    )
                    
                    fig_party.update_layout(height=400, font_size=10)
                    st.plotly_chart(fig_party, use_container_width=True)
                    
                    # Party summary metrics
                    total_party_votes = party_data['Votes'].sum()
                    party_candidates = party_data['Name'].nunique()
                    st.metric(f"{party} Total Votes", f"{total_party_votes:,}")
                    st.metric(f"{party} Candidates", party_candidates)
                else:
                    st.info(f"No data for {party}")
        
        st.markdown("---")  # Separator line
    
    if not filtered_df.empty:
        # Remove rows with zero or null votes for cleaner visualization
        filtered_df = filtered_df[filtered_df['Votes'] > 0]
        
        # Create multiple sunburst views
        tab_sun1, tab_sun2, tab_sun3 = st.tabs(["🎯 Candidate → Prabhag", "🏛️ Prabhag → Candidate", "🔄 Round → Party → Prabhag"])
        
        with tab_sun1:
            st.subheader(f"{selected_election}: Candidate → Prabhag Analysis")
            
            # Aggregate data for sunburst but keep party info for coloring
            sunburst_data1 = filtered_df.groupby(['Name', 'Party', 'Prabhag'])['Votes'].sum().reset_index()
            
            fig_sun1 = px.sunburst(
                sunburst_data1,
                path=['Name', 'Prabhag'],
                values='Votes',
                color='Party',
                color_discrete_map=PARTY_COLORS,
                title=f"{selected_election} - Vote Distribution by Candidate → Prabhag"
            )
            
            fig_sun1.update_traces(
                textinfo="label+value",
                hovertemplate='<b>%{label}</b><br>Votes: %{value:,}<br>% of Parent: %{percentParent}<br>% of Total: %{percentRoot}<extra></extra>'
            )
            
            fig_sun1.update_layout(height=650, font_size=11)
            st.plotly_chart(fig_sun1, use_container_width=True)
        
        with tab_sun2:
            st.subheader(f"{selected_election}: Prabhag → Candidate Analysis")
            
            # Different hierarchy for geographic analysis (keeping party info for coloring only)
            sunburst_data2 = filtered_df.groupby(['Prabhag', 'Name', 'Party'])['Votes'].sum().reset_index()
            
            fig_sun2 = px.sunburst(
                sunburst_data2,
                path=['Prabhag', 'Name'],
                values='Votes',
                color='Party',
                color_discrete_map=PARTY_COLORS,
                title=f"{selected_election} - Geographic Distribution by Prabhag → Candidate"
            )
            
            fig_sun2.update_traces(
                textinfo="label+value",
                hovertemplate='<b>%{label}</b><br>Votes: %{value:,}<br>% of Parent: %{percentParent}<br>% of Total: %{percentRoot}<extra></extra>'
            )
            
            fig_sun2.update_layout(height=650, font_size=11)
            st.plotly_chart(fig_sun2, use_container_width=True)
        
        with tab_sun3:
            if len(selected_rounds) > 1:
                st.subheader(f"{selected_election}: Round → Party → Prabhag Analysis")
                
                # Round-wise analysis
                sunburst_data3 = filtered_df.groupby(['Round', 'Party', 'Prabhag'])['Votes'].sum().reset_index()
                sunburst_data3['Round'] = 'Round ' + sunburst_data3['Round'].astype(str)
                
                fig_sun3 = px.sunburst(
                    sunburst_data3,
                    path=['Round', 'Party', 'Prabhag'],
                    values='Votes',
                    color='Party',
                    color_discrete_map=PARTY_COLORS,
                    title=f"{selected_election} - Round-wise Performance by Round → Party → Prabhag"
                )
                
                fig_sun3.update_traces(
                    textinfo="label+percent parent+value",
                    hovertemplate='<b>%{label}</b><br>Votes: %{value:,}<br>% of Parent: %{percentParent}<br>% of Total: %{percentRoot}<extra></extra>'
                )
                
                fig_sun3.update_layout(height=650, font_size=11)
                st.plotly_chart(fig_sun3, use_container_width=True)
            else:
                st.info("Select multiple rounds to see round-wise comparison")
        
        # Enhanced Analytics Section
        st.header("📊 Detailed Performance Analytics")
        
        col_analytics1, col_analytics2 = st.columns(2)
        
        with col_analytics1:
            st.subheader("🏆 Top Performers by Prabhag")
            
            # Top performer in each prabhag
            top_performers = filtered_df.groupby(['Prabhag', 'Name', 'Party'])['Votes'].sum().reset_index()
            top_by_prabhag = top_performers.loc[top_performers.groupby('Prabhag')['Votes'].idxmax()]
            top_by_prabhag = top_by_prabhag.sort_values('Votes', ascending=False)
            
            st.dataframe(
                top_by_prabhag[['Prabhag', 'Name', 'Party', 'Votes']].rename(columns={
                    'Prabhag': 'Ward', 'Name': 'Winner', 'Party': 'Party', 'Votes': 'Votes'
                }),
                use_container_width=True
            )
        
        with col_analytics2:
            st.subheader("📈 Vote Share Analysis")
            
            # Party-wise vote share
            party_totals = filtered_df.groupby('Party')['Votes'].sum().reset_index()
            party_totals['Vote_Share'] = (party_totals['Votes'] / party_totals['Votes'].sum() * 100).round(2)
            party_totals = party_totals.sort_values('Votes', ascending=False)
            
            fig_vote_share = px.pie(
                party_totals, 
                values='Votes', 
                names='Party',
                title=f"{selected_election} - Party Vote Share",
                color='Party',
                color_discrete_map=PARTY_COLORS,
                hole=0.4
            )
            
            fig_vote_share.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>Votes: %{value:,}<br>Share: %{percent}<extra></extra>'
            )
            
            st.plotly_chart(fig_vote_share, use_container_width=True)
        
        # Performance Metrics Dashboard
        st.header("🎯 Key Performance Indicators")
        
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            total_votes = filtered_df['Votes'].sum()
            st.metric("Total Votes Cast", f"{total_votes:,}")
        
        with metric_col2:
            unique_candidates = filtered_df['Name'].nunique()
            st.metric("Total Candidates", unique_candidates)
        
        with metric_col3:
            unique_prabhags = filtered_df['Prabhag'].nunique()
            st.metric("Prabhags Covered", unique_prabhags)
        
        with metric_col4:
            avg_votes_per_prabhag = (total_votes / unique_prabhags) if unique_prabhags > 0 else 0
            st.metric("Avg Votes/Prabhag", f"{avg_votes_per_prabhag:,.0f}")
        
        # Detailed Comparison Table
        st.subheader("📋 Comprehensive Results Table")
        
        # Create enhanced pivot table
        detailed_pivot = filtered_df.groupby(['Name', 'Party', 'Prabhag'])['Votes'].sum().reset_index()
        comparison_table = detailed_pivot.pivot_table(
            index=['Name', 'Party'], 
            columns='Prabhag', 
            values='Votes', 
            fill_value=0
        )
        
        # Add summary statistics
        comparison_table['Total_Votes'] = comparison_table.sum(axis=1)
        comparison_table['Avg_Per_Prabhag'] = comparison_table['Total_Votes'] / unique_prabhags
        comparison_table['Max_Prabhag_Votes'] = comparison_table.iloc[:, :-2].max(axis=1)
        comparison_table['Min_Prabhag_Votes'] = comparison_table.iloc[:, :-3].min(axis=1)
        
        # Sort by total votes
        comparison_table = comparison_table.sort_values('Total_Votes', ascending=False)
        
        st.dataframe(comparison_table, use_container_width=True)
        
    else:
        st.warning(f"No data found for the selected filters: {selected_election} with selected parties and rounds.")

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
