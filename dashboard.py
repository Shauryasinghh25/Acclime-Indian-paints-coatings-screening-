import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(
    page_title="Indian Paints & Coatings M&A Intelligence",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

BASE_DIR = Path(__file__).resolve().parent

@st.cache_data
def load_datasets():
    screening_df = pd.read_csv(BASE_DIR / "acquisition_screening.csv")
    company_master_df = pd.read_csv(BASE_DIR / "company_master.csv")
    financial_df = pd.read_csv(BASE_DIR / "financial_analysis.csv")
    plants_df = pd.read_csv(BASE_DIR / "plant_locations.csv")
    ownership_df = pd.read_csv(BASE_DIR / "ownership_analysis.csv")
    evidence_df = pd.read_csv(BASE_DIR / "evidence_register.csv")
    coverage_df = pd.read_csv(BASE_DIR / "coverage_report.csv")
    return screening_df, company_master_df, financial_df, plants_df, ownership_df, evidence_df, coverage_df

screening_df, company_master_df, financial_df, plants_df, ownership_df, evidence_df, coverage_df = load_datasets()

st.sidebar.title("🎨 Paints & Coatings M&A")
st.sidebar.caption("Evidence-Backed M&A Screening & Company Intelligence")

rec_filter = st.sidebar.multiselect(
    "Filter by Recommendation",
    options=screening_df["recommendation"].unique(),
    default=screening_df["recommendation"].unique()
)

segment_options = ["All"] + sorted(list(company_master_df["primary_segment"].dropna().unique()))
selected_segment = st.sidebar.selectbox("Filter by Product Segment", segment_options)

state_options = ["All"] + sorted(list(company_master_df["registered_state"].dropna().unique()))
selected_state = st.sidebar.selectbox("Filter by Registered State", state_options)

max_revenue = st.sidebar.slider(
    "Max Revenue Threshold (₹ Crore)",
    min_value=10.0,
    max_value=35000.0,
    value=1000.0,
    step=50.0
)

filtered_screening = screening_df[screening_df["recommendation"].isin(rec_filter)]
if selected_segment != "All":
    filtered_screening = filtered_screening[filtered_screening["primary_segment"] == selected_segment]

merged_df = filtered_screening.merge(
    company_master_df[["company_id", "registered_state", "website", "incorporation_year"]],
    on="company_id",
    how="left"
)

if selected_state != "All":
    merged_df = merged_df[merged_df["registered_state"] == selected_state]

st.title("Indian Paints & Coatings Industry — M&A Screening & Intelligence")
st.markdown(f"Comprehensive intelligence platform covering **{len(company_master_df)} audited legal entities**, **{len(plants_df)} manufacturing plants**, and **{len(evidence_df)} field-level verified citations** focusing on targets below **₹1,000 crore**.")

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
total_targets = (screening_df["recommendation"] == "SHORTLIST — POTENTIAL ACQUISITION TARGET").sum()
pass_count = (screening_df["recommendation"] == "PASS").sum()
total_plants = len(plants_df)
total_cits = len(evidence_df)

kpi1.metric("Shortlisted Targets", f"{total_targets}", delta="< ₹1,000 Cr Mandate")
kpi2.metric("Excluded (PASS)", f"{pass_count}", delta="Large Cap / Traders")
kpi3.metric("Verified Plants", f"{total_plants}", delta="14 States")
kpi4.metric("Evidence Citations", f"{total_cits}", delta="100% Traceable")
kpi5.metric("Avg EBITDA Margin", f"{financial_df['ebitda_margin_pct'].mean():.1f}%", delta="Historical Avg")

st.divider()

tabs = st.tabs([
    "🎯 M&A Target Screening",
    "📊 Financial Intelligence",
    "🏭 Plant Footprint",
    "👥 Ownership & Promoters",
    "📑 Evidence Register",
    "📋 Coverage Summary & Exports"
])

with tabs[0]:
    st.subheader("🎯 Target Screening & Acquisition Funnel")
    
    col_chart, col_funnel = st.columns([3, 2])
    
    with col_chart:
        plot_df = merged_df[merged_df["revenue_inr_cr"].notna()].copy()
        plot_df = plot_df.merge(
            financial_df.groupby("company_id")["ebitda_margin_pct"].last().reset_index(),
            on="company_id",
            how="left"
        )
        
        fig = px.scatter(
            plot_df[plot_df["revenue_inr_cr"] <= max_revenue],
            x="revenue_inr_cr",
            y="ebitda_margin_pct",
            color="primary_segment",
            size="revenue_inr_cr",
            hover_name="canonical_name",
            hover_data=["listing_status", "registered_state"],
            title=f"Revenue (₹ Cr) vs. EBITDA Margin (%) [Filtered <= ₹{max_revenue:.0f} Cr]",
            labels={"revenue_inr_cr": "Annual Revenue (₹ Crore)", "ebitda_margin_pct": "EBITDA Margin (%)"},
            template="plotly_white",
            height=400
        )
        fig.add_vline(x=1000.0, line_dash="dash", line_color="red", annotation_text="₹1,000 Cr Cap")
        st.plotly_chart(fig, use_container_width=True)

    with col_funnel:
        st.markdown("#### Screening Breakdown")
        seg_counts = merged_df["recommendation"].value_counts().reset_index()
        seg_counts.columns = ["Recommendation", "Count"]
        fig_pie = px.pie(
            seg_counts,
            values="Count",
            names="Recommendation",
            hole=0.4,
            color="Recommendation",
            color_discrete_map={
                "SHORTLIST — POTENTIAL ACQUISITION TARGET": "#2ca02c",
                "PASS": "#d62728",
                "PENDING VERIFICATION": "#ff7f0e"
            },
            height=350
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("#### Screened Companies List")
    disp_cols = [
        "canonical_name", "listing_status", "primary_segment", "revenue_inr_cr",
        "financial_year", "recommendation", "recommendation_rationale", "key_risks"
    ]
    st.dataframe(
        merged_df[disp_cols].sort_values("revenue_inr_cr", ascending=False),
        use_container_width=True,
        hide_index=True
    )

with tabs[1]:
    st.subheader("📊 3-Year Historical Financial Performance")
    
    selected_comp = st.selectbox(
        "Select Company to Analyze Financials:",
        options=sorted(list(financial_df["canonical_name"].unique()))
    )
    
    comp_fin = financial_df[financial_df["canonical_name"] == selected_comp].sort_values("financial_year")
    
    c1, c2 = st.columns(2)
    with c1:
        fig_rev = px.bar(
            comp_fin,
            x="financial_year",
            y=["revenue_cr", "ebitda_cr", "pat_cr"],
            barmode="group",
            title=f"{selected_comp} - Revenue, EBITDA & PAT (₹ Crore)",
            labels={"value": "₹ Crore", "financial_year": "Financial Year", "variable": "Metric"},
            template="plotly_white",
            height=360
        )
        st.plotly_chart(fig_rev, use_container_width=True)

    with c2:
        fig_ratios = px.line(
            comp_fin,
            x="financial_year",
            y=["ebitda_margin_pct", "net_profit_margin_pct"],
            markers=True,
            title=f"{selected_comp} - Margin Trajectory (%)",
            labels={"value": "Percentage (%)", "financial_year": "Financial Year", "variable": "Ratio"},
            template="plotly_white",
            height=360
        )
        st.plotly_chart(fig_ratios, use_container_width=True)

    st.markdown(f"#### Complete Financial Records: {selected_comp}")
    st.dataframe(comp_fin, use_container_width=True, hide_index=True)

with tabs[2]:
    st.subheader("🏭 Operating Footprint & Manufacturing Plant Mapping")
    
    state_plants = plants_df["state"].value_counts().reset_index()
    state_plants.columns = ["State", "Plant Count"]
    
    col_p1, col_p2 = st.columns([2, 3])
    with col_p1:
        fig_plants = px.bar(
            state_plants,
            x="Plant Count",
            y="State",
            orientation="h",
            title="Manufacturing Plants by State",
            color="Plant Count",
            color_continuous_scale="Blues",
            template="plotly_white",
            height=420
        )
        fig_plants.update_layout(yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig_plants, use_container_width=True)

    with col_p2:
        st.markdown("#### Facility Distribution Overview")
        st.info("Operating plants are heavily concentrated along major chemical and automotive manufacturing corridors: **Gujarat (GIDC Padra, Ankleshwar, Savli, Vapi)**, **Maharashtra (MIDC Ambernath, Tarapur, Nashik, Pune)**, **Haryana (HSIIDC Sonipat, Faridabad, Manesar)**, and **Tamil Nadu (SIPCOT Ambattur, Ranipet, Oragadam)**.")
        st.metric("Total Documented Facilities", f"{len(plants_df)}")
        st.metric("Unique Manufacturing Hub Cities", f"{plants_df['city'].nunique()}")

    st.markdown("#### Detailed Manufacturing Facilities Directory")
    st.dataframe(
        plants_df[["company_name", "facility_name", "facility_address", "city", "state", "products_manufactured", "stated_capacity", "land_ownership", "source_url"]],
        use_container_width=True,
        hide_index=True
    )

with tabs[3]:
    st.subheader("👥 Shareholding, Governance & Acquisition Diligence")
    
    col_o1, col_o2 = st.columns(2)
    with col_o1:
        type_counts = ownership_df["owner_type"].value_counts().reset_index()
        type_counts.columns = ["Owner Type", "Count"]
        fig_owner = px.pie(
            type_counts,
            values="Count",
            names="Owner Type",
            hole=0.4,
            title="Ownership Category Distribution",
            template="plotly_white",
            height=360
        )
        st.plotly_chart(fig_owner, use_container_width=True)

    with col_o2:
        st.markdown("#### Strategic Ownership Highlights")
        st.markdown("""
        * **Closely Held Regional Leaders:** Promoters hold >50% to 100% equity in standout targets like **Grand Polycoats**, **Sheenlac Paints**, and **Surfa Coats**, facilitating direct bilateral transaction discussions.
        * **Foreign Technology & Joint Ventures:** Key entities maintain global partnerships: **Sirca Paints** with *Sirca S.p.A. Italy*, **Siddhika Coatings** with *SKK Japan*, and **Kirloskar Corrocoat** with *Corrocoat UK*.
        * **Corporate Group Backing:** Entities such as **IVP Limited** (*Allana Group*) and **Gem Paints** (*Astral Limited majority stake*) demonstrate precedent platform-build acquisitions.
        """)

    st.markdown("#### Full Ownership Register")
    st.dataframe(
        ownership_df[["company_name", "owner_name", "owner_type", "holding_percentage", "as_of_date", "is_controlling", "source_url"]],
        use_container_width=True,
        hide_index=True
    )

with tabs[4]:
    st.subheader("📑 Traceable Field-Level Evidence Register")
    st.markdown("Every material company claim, revenue figure, facility address, and ownership record is directly cited with source URLs and verified excerpts.")
    
    search_claim = st.text_input("Search Evidence Excerpts or Facts:", "")
    disp_ev = evidence_df
    if search_claim:
        disp_ev = disp_ev[disp_ev["claim_fact"].str.contains(search_claim, case=False, na=False) | disp_ev["exact_text_excerpt"].str.contains(search_claim, case=False, na=False)]

    st.dataframe(
        disp_ev[["company_name", "claim_type", "claim_fact", "page_or_section", "verification_status", "exact_text_excerpt", "source_url"]],
        use_container_width=True,
        hide_index=True
    )

with tabs[5]:
    st.subheader("📋 Pipeline Coverage Report & Download Center")
    
    st.table(coverage_df)
    
    st.divider()
    st.markdown("### 📥 Download Deliverable Files")
    
    c_d1, c_d2, c_d3 = st.columns(3)
    with c_d1:
        with open(BASE_DIR / "acquisition_screening.csv", "rb") as f:
            st.download_button("Download Acquisition Screening (CSV)", f, "acquisition_screening.csv", "text/csv")
        with open(BASE_DIR / "company_master.csv", "rb") as f:
            st.download_button("Download Company Master (CSV)", f, "company_master.csv", "text/csv")
        with open(BASE_DIR / "financial_analysis.csv", "rb") as f:
            st.download_button("Download Financial Analysis (CSV)", f, "financial_analysis.csv", "text/csv")

    with c_d2:
        with open(BASE_DIR / "plant_locations.csv", "rb") as f:
            st.download_button("Download Plant Locations (CSV)", f, "plant_locations.csv", "text/csv")
        with open(BASE_DIR / "ownership_analysis.csv", "rb") as f:
            st.download_button("Download Ownership Analysis (CSV)", f, "ownership_analysis.csv", "text/csv")
        with open(BASE_DIR / "evidence_register.csv", "rb") as f:
            st.download_button("Download Evidence Register (CSV)", f, "evidence_register.csv", "text/csv")

    with c_d3:
        with open(BASE_DIR / "excluded_companies.csv", "rb") as f:
            st.download_button("Download Excluded Companies (CSV)", f, "excluded_companies.csv", "text/csv")
        with open(BASE_DIR / "coverage_report.csv", "rb") as f:
            st.download_button("Download Coverage Report (CSV)", f, "coverage_report.csv", "text/csv")
        with open(BASE_DIR / "indian_paints_mna_database.xlsx", "rb") as f:
            st.download_button("Download Full Excel Database (XLSX)", f, "indian_paints_mna_database.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

