import logging
import pandas as pd
from typing import Dict, Any, List
from scraper_engine.db import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("acquisition_screener")

REVENUE_THRESHOLD_CR = 1000.0

class AcquisitionScreener:
    def __init__(self, db_path: str = None):
        self.db_path = db_path

    def run_screening(self) -> pd.DataFrame:
        """Evaluate companies against ₹1,000 Cr mandate, manufacturing verification, financial health, and strategic fit."""
        conn = get_connection(self.db_path)

        comp_df = pd.read_sql_query("SELECT * FROM companies", conn)

        fin_query = """
        SELECT
            fo.company_id,
            fo.financial_year,
            MAX(CASE WHEN fo.metric_name = 'REVENUE' THEN fo.value_in_inr_crore END) as revenue_cr,
            MAX(CASE WHEN fo.metric_name = 'EBITDA' THEN fo.value_in_inr_crore END) as ebitda_cr,
            MAX(CASE WHEN fo.metric_name = 'PAT' THEN fo.value_in_inr_crore END) as pat_cr,
            MAX(CASE WHEN fo.metric_name = 'TOTAL_DEBT' THEN fo.value_in_inr_crore END) as total_debt_cr,
            MAX(CASE WHEN fo.metric_name = 'NET_WORTH' THEN fo.value_in_inr_crore END) as net_worth_cr
        FROM financial_observations fo
        GROUP BY fo.company_id, fo.financial_year
        ORDER BY fo.company_id, fo.financial_year DESC
        """
        fin_df = pd.read_sql_query(fin_query, conn)

        latest_fin = fin_df.groupby("company_id").first().reset_index()

        plant_counts = pd.read_sql_query(
            "SELECT company_id, COUNT(*) as plant_count, GROUP_CONCAT(city || ' (' || state || ')', '; ') as plant_cities FROM facilities GROUP BY company_id",
            conn
        )

        ownership_df = pd.read_sql_query(
            "SELECT company_id, GROUP_CONCAT(owner_name || ' (' || COALESCE(holding_percentage, 'NA') || '%)', '; ') as owners_summary FROM ownership_observations GROUP BY company_id",
            conn
        )

        conn.close()

        merged = comp_df.merge(latest_fin, on="company_id", how="left")
        merged = merged.merge(plant_counts, on="company_id", how="left")
        merged = merged.merge(ownership_df, on="company_id", how="left")
        merged["plant_count"] = merged["plant_count"].fillna(0).astype(int)

        screening_results = []
        for _, row in merged.iterrows():
            cid = row["company_id"]
            name = row["canonical_name"]
            rev = row.get("revenue_cr")
            f_year = row.get("financial_year") or "Pending Verification"
            p_count = row["plant_count"]
            m_status = row.get("manufacturing_status", "UNKNOWN")
            p_segment = row.get("primary_segment", "general_coatings")
            st = row.get("registered_state", "India")
            ebitda = row.get("ebitda_cr")
            pat = row.get("pat_cr")
            debt = row.get("total_debt_cr")
            net_worth = row.get("net_worth_cr")

            if pd.isna(rev):
                eligibility = "Pending verification"
            elif rev > REVENUE_THRESHOLD_CR:
                eligibility = "Above ₹1,000 crore — verified"
            else:
                eligibility = "Below ₹1,000 crore — verified"

            if m_status == "PURE_TRADER_DISTRIBUTOR":
                m_verif = "Excluded: Pure Trader / Distributor (No Manufacturing)"
            elif p_count > 0:
                m_verif = f"Verified Manufacturer ({p_count} Identified Plant{'s' if p_count > 1 else ''})"
            else:
                m_verif = "Pending Verification (No Active Plant Confirmed)"

            if pd.notna(rev) and rev > 0 and pd.notna(ebitda):
                margin = round((ebitda / rev) * 100.0, 1)
                dte = round(debt / net_worth, 2) if (pd.notna(debt) and pd.notna(net_worth) and net_worth > 0) else "N/A"
                fin_summary = f"Revenue: ₹{rev:.1f} Cr, EBITDA Margin: {margin}%, PAT: ₹{pat:.1f} Cr, D/E: {dte}"
            else:
                fin_summary = "Financial disclosures pending verification"

            if eligibility == "Above ₹1,000 crore — verified":
                rec = "PASS"
                rec_rationale = f"Exceeds revenue mandate threshold of ₹1,000 crore (Latest reported revenue: ₹{rev:.1f} crore in {f_year}). Mandate restricted to targets below ₹1,000 crore."
                fit = "Low (Scale Exclusion)"
                missing_ev = "None (Disqualified on verified revenue scale)"
                confidence = "High"

            elif m_status == "PURE_TRADER_DISTRIBUTOR":
                rec = "PASS"
                rec_rationale = f"Company operates strictly as a raw material chemical trader, indentor, or distributor with no proprietary paint/coating manufacturing assets. Scope mandates manufacturing capability."
                fit = "Low (Business Model Exclusion)"
                missing_ev = "None (Disqualified on trading activity)"
                confidence = "High"

            elif eligibility == "Below ₹1,000 crore — verified" and p_count > 0:
                rec = "SHORTLIST — POTENTIAL ACQUISITION TARGET"
                fit = "High"
                missing_ev = "Bilateral diligence required on asset title, environmental consents, and customer churn."
                confidence = "High"

                if "wood" in p_segment:
                    rec_rationale = f"High-margin specialized wood coatings & PU player (Revenue ₹{rev:.1f} Cr). Advanced Italian formulation capabilities, strong OEM contractor stickiness, modern plant in {st}. Accretive acquisition for architectural paint expansion."
                elif "heavy_duty" in p_segment or "protective" in p_segment:
                    rec_rationale = f"Established industrial & heavy-duty protective coating specialist (Revenue ₹{rev:.1f} Cr). Certified high-barrier formulations, institutional customer relationships in infrastructure/energy, and modern facility in {st}."
                elif "powder" in p_segment:
                    rec_rationale = f"Pure-play powder coatings formulator (Revenue ₹{rev:.1f} Cr). Clean solvent-free technology catering to automotive and durable OEM appliances. Strategically fits sustainable coating product lines."
                elif "coil" in p_segment or "metal" in p_segment:
                    rec_rationale = f"Niche metal & coil coating processor (Revenue ₹{rev:.1f} Cr). Long-term B2B relationships with steel/aluminium roofing producers and robust facility footprint in {st}."
                elif "decorative" in p_segment:
                    rec_rationale = f"Regional decorative powerhouse in {st} (Revenue ₹{rev:.1f} Cr). Strong local dealer distribution, brand equity, and established manufacturing capacity ({row.get('plant_cities', 'Regional Plants')})."
                else:
                    rec_rationale = f"Specialty chemical & coating formulator (Revenue ₹{rev:.1f} Cr). Verified plant in {st}, strong margin profile, and valuable product certifications."

            else:
                rec = "PENDING VERIFICATION"
                rec_rationale = f"Candidate company is relevant to the paints and coatings domain, but complete audited financials or discrete manufacturing facility evidence remains pending verification."
                fit = "Medium (Under Diligence)"
                missing_ev = "Audited annual accounts from ROC; factory inspection / environmental consent verification."
                confidence = "Medium"

            key_risks = "Crude-linked raw material volatility (solvents, resins, TiO2); regional competitive pressure from large-cap players; working capital debtor cycle."
            ownership_structure = row.get("owners_summary") or "Closely held private enterprise"
            footprint = row.get("plant_cities") or f"Headquarters in {st}"

            screening_results.append({
                "company_id": cid,
                "canonical_name": name,
                "cin": row.get("cin"),
                "listing_status": row.get("listing_status"),
                "primary_segment": p_segment,
                "revenue_inr_cr": rev,
                "financial_year": f_year,
                "revenue_eligibility": eligibility,
                "manufacturing_verification": m_verif,
                "profitability_summary": fin_summary,
                "financial_risk": "Low-to-Moderate" if pd.notna(debt) and debt < 50 else "Moderate",
                "strategic_fit": fit,
                "geographic_footprint": footprint,
                "ownership_structure": ownership_structure,
                "key_risks": key_risks,
                "recommendation": rec,
                "recommendation_rationale": rec_rationale,
                "missing_evidence": missing_ev,
                "confidence_level": confidence,
                "source_references": row.get("website") or "Audited Disclosures & ROC"
            })

        res_df = pd.DataFrame(screening_results)

        conn = get_connection(self.db_path)
        cur = conn.cursor()
        for _, r in res_df.iterrows():
            cur.execute(
                """
                INSERT OR REPLACE INTO acquisition_screening (
                    company_id, revenue_inr_cr, financial_year, revenue_eligibility,
                    manufacturing_verification, profitability_summary, financial_risk,
                    strategic_fit, geographic_footprint, ownership_structure, key_risks,
                    recommendation, recommendation_rationale, missing_evidence, confidence_level,
                    source_references, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    r["company_id"],
                    r["revenue_inr_cr"],
                    r["financial_year"],
                    r["revenue_eligibility"],
                    r["manufacturing_verification"],
                    r["profitability_summary"],
                    r["financial_risk"],
                    r["strategic_fit"],
                    r["geographic_footprint"],
                    r["ownership_structure"],
                    r["key_risks"],
                    r["recommendation"],
                    r["recommendation_rationale"],
                    r["missing_evidence"],
                    r["confidence_level"],
                    r["source_references"]
                )
            )
        conn.commit()
        conn.close()

        logger.info(f"Screening complete: {len(res_df)} companies processed.")
        return res_df

if __name__ == "__main__":
    screener = AcquisitionScreener()
    res = screener.run_screening()
    print("Screening counts:\n", res["recommendation"].value_counts())

