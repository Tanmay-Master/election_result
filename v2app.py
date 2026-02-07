import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from fpdf import FPDF
import tempfile
import os
import io
from PIL import Image

# -----------------------------------------------------------------------------
# 1. Page Configuration & Data Loading
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Election Analysis 2025", layout="wide")

st.title("🗳️ Election Intelligence & Margin Analysis Dashboard (2025)")

@st.cache_data
def load_data():
    try:
        # Note: Ensure election.csv is in the same directory
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

if df.empty:
    st.warning("Please upload 'election.csv' to proceed.")
    st.stop()

# Define Global Color Mapping for consistency
PARTY_COLORS = {
    "BJP": "Blue",
    "SS": "Orange",
    "SS-UBT": "violet",
    "Independent": "gray",
    "independent": "gray",
    "Nota": "black"
}

# -----------------------------------------------------------------------------
# 2. Custom PDF Class for Watermark
# -----------------------------------------------------------------------------
class PDF_With_Watermark(FPDF):
    def __init__(self, watermark_text=""):
        super().__init__()
        self.watermark_text = watermark_text

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'L')
        if self.watermark_text:
            self.cell(0, 10, self.watermark_text, 0, 0, 'R')

# -----------------------------------------------------------------------------
# 3. Sidebar Filter Configuration
# -----------------------------------------------------------------------------
st.sidebar.header("📁 PDF Report Configuration")
def natural_sort_key(s):
    return int(s) if s.isdigit() else s

unique_prabhags = sorted(df['Prabhag'].unique(), key=natural_sort_key)
unique_parties = sorted(df['Party'].unique())

selected_pdf_prabhags = st.sidebar.multiselect(
    "Select Prabhags for PDF:", unique_prabhags, default=unique_prabhags
)

selected_pdf_parties = st.sidebar.multiselect(
    "Select Parties for PDF:", unique_parties, default=unique_parties
)

# -----------------------------------------------------------------------------
# 4. Enhanced PDF Generation Function (FIXED)
# -----------------------------------------------------------------------------
def generate_pdf(data, prabhag_list, party_list, watermark_text):
    pdf = PDF_With_Watermark(watermark_text=watermark_text)
    pdf.set_auto_page_break(auto=True, margin=15)
    
    filtered_df = data[
        (data['Prabhag'].isin(prabhag_list)) & 
        (data['Party'].isin(party_list))
    ]
    
    report_prabhags = sorted(filtered_df['Prabhag'].unique(), key=natural_sort_key)
    
    if not report_prabhags:
        return None

    progress_bar = st.progress(0)
    
    for i, prabhag in enumerate(report_prabhags):
        pdf.add_page()
        pdf.set_font("Helvetica", 'B', 16)
        pdf.cell(200, 10, txt=f"Election Report: Prabhag {prabhag}", ln=True, align='C')
        pdf.ln(5)
        
        p_df = filtered_df[filtered_df['Prabhag'] == prabhag]
        chart_data = p_df.groupby(['Name', 'Party', 'Election_type'])['Votes'].sum().reset_index()
        chart_data = chart_data.sort_values(by=['Party', 'Votes'], ascending=[True, False])
        
        # --- Create Graph with simpler layout to avoid Kaleido issues ---
        fig = px.bar(
            chart_data, 
            x='Name', 
            y='Votes', 
            color='Party', 
            text='Votes', 
            template="plotly_white",
            title=f"Vote Distribution - Prabhag {prabhag}",
            color_discrete_map=PARTY_COLORS
        )
        fig.update_xaxes(type='category')
        fig.update_traces(textposition='outside')
        fig.update_layout(
            title_x=0.5,
            title_font_size=16,
            showlegend=True,
            # Simplify layout to prevent serialization issues
            xaxis_title="Candidate",
            yaxis_title="Votes",
            font=dict(size=12)
        )
        
        # --- Alternative 1: Use PIL to create image if Kaleido fails ---
        try:
            # Try with lower resolution first
            img_bytes = fig.to_image(format="png", engine="kaleido", width=1000, height=600)
            img = Image.open(io.BytesIO(img_bytes))
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
                img.save(tmpfile.name, "PNG", dpi=(150, 150))
                pdf.image(tmpfile.name, x=10, y=35, w=190)
                tmp_path = tmpfile.name
            
            # Clean up
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                
        except Exception as e:
            st.warning(f"Using alternative method for Prabhag {prabhag}: {str(e)[:100]}")
            # Alternative 2: Create a simple table if chart fails
            pdf.set_font("Helvetica", 'B', 12)
            pdf.cell(200, 10, txt="Candidate Vote Summary (Chart unavailable):", ln=True)
            pdf.ln(5)
            
            # Create a simple table
            pdf.set_font("Helvetica", '', 10)
            for idx, row in chart_data.iterrows():
                line = f"{row['Name']} ({row['Party']}): {row['Votes']:,} votes"
                pdf.cell(200, 8, txt=line, ln=True)
            
            pdf.ln(10)
        
        progress_bar.progress((i + 1) / len(report_prabhags))

    # FIX: Properly handle PDF output for Streamlit
    try:
        # Method 1: Try to get as bytes
        pdf_output = pdf.output(dest='S')
        if isinstance(pdf_output, str):
            # For older fpdf versions that return string
            return pdf_output.encode('latin-1')
        elif isinstance(pdf_output, bytearray):
            # Convert bytearray to bytes
            return bytes(pdf_output)
        else:
            return pdf_output
    except:
        # Method 2: Use alternative approach
        try:
            return pdf.output()
        except:
            # Final fallback
            return b'PDF generation failed'

# -----------------------------------------------------------------------------
# 5. App Tabs
# -----------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🎯 Margin Comparison", "🔢 Data Tables", "🖨️ Export Center"])

# --- TAB 1: DASHBOARD ---
with tab1:
    st.header("Prabhag Wise Distribution")
    selected_p = st.selectbox("View Dashboard for Prabhag:", unique_prabhags)
    dash_df = df[df['Prabhag'] == selected_p]
    chart_dash = dash_df.groupby(['Name', 'Party', 'Election_type'])['Votes'].sum().reset_index()
    fig_dash = px.bar(
        chart_dash, x='Name', y='Votes', color='Party', text='Votes', 
        barmode='group', template="plotly_white", height=500,
        color_discrete_map=PARTY_COLORS
    )
    fig_dash.update_xaxes(type='category')
    fig_dash.update_traces(textposition='outside')
    st.plotly_chart(fig_dash, use_container_width=True)

# --- TAB 2: MARGIN COMPARISON ---
with tab2:
    st.header("Victory Margin Analysis (Winner vs Runner-up)")
    
    m_agg = df.groupby(['Prabhag', 'Election_type', 'Name', 'Party'])['Votes'].sum().reset_index()
    m_agg = m_agg.sort_values(['Prabhag', 'Election_type', 'Votes'], ascending=[True, True, False])
    
    top_2 = m_agg.groupby(['Prabhag', 'Election_type']).head(2).copy()
    top_2['Rank'] = top_2.groupby(['Prabhag', 'Election_type']).cumcount() + 1
    
    pivot = top_2.pivot(index=['Prabhag', 'Election_type'], columns='Rank', values=['Name', 'Party', 'Votes']).reset_index()
    pivot.columns = ['Prabhag', 'Category', 'Winner', 'RunnerUp', 'Win_Party', 'Run_Party', 'Win_Votes', 'Run_Votes']
    pivot['Margin'] = (pivot['Win_Votes'] - pivot['Run_Votes'].fillna(0)).astype(int)
    pivot['Party_Fight'] = pivot['Win_Party'] + " vs " + pivot['Run_Party'].fillna("N/A")
    
    pivot['P_Sort'] = pd.to_numeric(pivot['Prabhag'], errors='coerce')
    pivot = pivot.sort_values(['P_Sort', 'Category']).drop(columns=['P_Sort'])

    cat_filter = st.multiselect("Filter by Election Type:", sorted(pivot['Category'].unique()), default=sorted(pivot['Category'].unique()))
    filtered_margin = pivot[pivot['Category'].isin(cat_filter)]

    fig_margin = px.bar(
        filtered_margin, 
        x='Prabhag', 
        y='Margin', 
        color='Win_Party', 
        facet_col='Category',
        text='Margin',
        hover_data=['Winner', 'RunnerUp', 'Party_Fight'],
        title="Victory Margin Comparison (Grouped by Category)",
        template="plotly_white",
        color_discrete_map=PARTY_COLORS
    )
    fig_margin.update_traces(textposition='outside')
    st.plotly_chart(fig_margin, use_container_width=True)

    st.subheader("Detailed Category-wise Comparison Table")
    st.dataframe(filtered_margin[['Prabhag', 'Category', 'Winner', 'Win_Party', 'RunnerUp', 'Run_Party', 'Margin']], use_container_width=True)

# --- TAB 3: DATA TABLES ---
with tab3:
    st.header("Consolidated Election Data")
    table_df = df.groupby(['Prabhag', 'Election_type', 'Party', 'Name'])['Votes'].sum().reset_index()
    table_df['P_Sort'] = pd.to_numeric(table_df['Prabhag'], errors='coerce')
    table_df = table_df.sort_values(['P_Sort', 'Votes'], ascending=[True, False]).drop(columns=['P_Sort'])
    st.dataframe(table_df, use_container_width=True)

# --- TAB 4: EXPORT CENTER ---
with tab4:
    st.header("Download PDF Reports")
    watermark = st.text_input("Enter Watermark Text (Corner Label):", value="Election Analysis 2025")
    
    # Add a note about potential issues
    st.info("⚠️ **Note**: If PDF generation fails, charts will be replaced with data tables. For large datasets, consider generating in smaller batches.")
    
    if st.button("🚀 Generate PDF Report"):
        if not selected_pdf_prabhags:
            st.error("Please select at least one Prabhag in the sidebar.")
        else:
            with st.spinner(f"Generating PDF for {len(selected_pdf_prabhags)} Prabhags..."):
                pdf_out = generate_pdf(df, selected_pdf_prabhags, selected_pdf_parties, watermark)
                
                if pdf_out and pdf_out != b'PDF generation failed':
                    st.success("✅ PDF generated successfully!")
                    
                    # Ensure we have bytes, not bytearray
                    if isinstance(pdf_out, bytearray):
                        pdf_out = bytes(pdf_out)
                    
                    st.download_button(
                        label="📥 Download PDF Report", 
                        data=pdf_out, 
                        file_name="Election_2025_Report.pdf", 
                        mime="application/pdf"
                    )
                else:
                    st.error("Failed to generate PDF. Please try with fewer Prabhags or check the data.")