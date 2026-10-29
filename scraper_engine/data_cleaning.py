import re
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from scraper_engine.db import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("data_cleaning")

STATE_NORMALIZATION_MAP = {
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "ncr": "Delhi",
    "haryana": "Haryana",
    "hr": "Haryana",
    "maharashtra": "Maharashtra",
    "mh": "Maharashtra",
    "gujarat": "Gujarat",
    "gj": "Gujarat",
    "tamil nadu": "Tamil Nadu",
    "tn": "Tamil Nadu",
    "karnataka": "Karnataka",
    "ka": "Karnataka",
    "uttar pradesh": "Uttar Pradesh",
    "up": "Uttar Pradesh",
    "west bengal": "West Bengal",
    "wb": "West Bengal",
    "rajasthan": "Rajasthan",
    "rj": "Rajasthan",
    "punjab": "Punjab",
    "pb": "Punjab",
    "goa": "Goa",
    "ga": "Goa",
    "telangana": "Telangana",
    "ts": "Telangana",
    "himachal pradesh": "Himachal Pradesh",
    "hp": "Himachal Pradesh",
    "odisha": "Odisha",
    "orissa": "Odisha",
    "kerala": "Kerala",
    "kl": "Kerala",
    "madhya pradesh": "Madhya Pradesh",
    "mp": "Madhya Pradesh",
    "andhra pradesh": "Andhra Pradesh",
    "ap": "Andhra Pradesh",
    "uttarakhand": "Uttarakhand",
    "uk": "Uttarakhand",
    "jharkhand": "Jharkhand",
    "bihar": "Bihar",
    "chhattisgarh": "Chhattisgarh"
}

CIN_PATTERN = re.compile(r'^[LUlu][0-9]{5}[A-Za-z]{2}[0-9]{4}[A-Za-z]{3}[0-9]{6}$')

class DataCleaner:
    def __init__(self, db_path: str = None):
        self.db_path = db_path

    @staticmethod
    def normalize_company_name(name: str) -> str:
        """Standardize company name by trimming whitespace and normalizing legal suffixes."""
        if not name or pd.isna(name):
            return ""
        s = re.sub(r'\s+', ' ', str(name)).strip()
        s = re.sub(r'\b(?:pvt\.?\s*ltd\.?|private\s+limited\.?)\b\.?', 'Private Limited', s, flags=re.IGNORECASE)
        s = re.sub(r'\b(?:ltd\.?|limited\.?)\b\.?(?!\s*private)', 'Limited', s, flags=re.IGNORECASE)
        return s.rstrip(".,; ").strip()

    @staticmethod
    def validate_cin(cin: Optional[str]) -> bool:
        """Check if CIN matches standard 21-character MCA structure."""
        if not cin or pd.isna(cin):
            return False
        return bool(CIN_PATTERN.match(str(cin).strip()))

    @staticmethod
    def normalize_state(state: Optional[str]) -> Optional[str]:
        """Normalize state name using taxonomy dictionary."""
        if not state or pd.isna(state):
            return None
        st_clean = str(state).strip().lower()
        return STATE_NORMALIZATION_MAP.get(st_clean, state.strip().title())

    @staticmethod
    def clean_website(url: Optional[str]) -> Optional[str]:
        """Normalize URL format."""
        if not url or pd.isna(url) or url == "None":
            return None
        u = str(url).strip()
        if not u.startswith("http://") and not u.startswith("https://"):
            u = "https://" + u
        return u.rstrip("/")

    def calculate_financial_ratios(self) -> pd.DataFrame:
        """Fetch financial observations from database and calculate revenue growth, EBITDA margin, net profit margin, debt-to-equity."""
        conn = get_connection(self.db_path)
        query = """
        SELECT
            fo.company_id,
            c.canonical_name,
            c.cin,
            c.listing_status,
            fo.financial_year,
            fo.reporting_type,
            MAX(CASE WHEN fo.metric_name = 'REVENUE' THEN fo.value_in_inr_crore END) as revenue_cr,
            MAX(CASE WHEN fo.metric_name = 'EBITDA' THEN fo.value_in_inr_crore END) as ebitda_cr,
            MAX(CASE WHEN fo.metric_name = 'PAT' THEN fo.value_in_inr_crore END) as pat_cr,
            MAX(CASE WHEN fo.metric_name = 'TOTAL_DEBT' THEN fo.value_in_inr_crore END) as total_debt_cr,
            MAX(CASE WHEN fo.metric_name = 'NET_WORTH' THEN fo.value_in_inr_crore END) as net_worth_cr,
            MAX(CASE WHEN fo.metric_name = 'TOTAL_ASSETS' THEN fo.value_in_inr_crore END) as total_assets_cr,
            MAX(CASE WHEN fo.metric_name = 'OPERATING_CASH_FLOW' THEN fo.value_in_inr_crore END) as cfo_cr
        FROM financial_observations fo
        JOIN companies c ON fo.company_id = c.company_id
        GROUP BY fo.company_id, c.canonical_name, c.cin, c.listing_status, fo.financial_year, fo.reporting_type
        ORDER BY fo.company_id, fo.financial_year ASC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            logger.warning("No financial records found in database for ratio computation.")
            return df

        num_cols = ["revenue_cr", "ebitda_cr", "pat_cr", "total_debt_cr", "net_worth_cr", "total_assets_cr", "cfo_cr"]
        for c in num_cols:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        df["ebitda_margin_pct"] = np.where(
            (df["revenue_cr"].notna()) & (df["revenue_cr"] > 0) & (df["ebitda_cr"].notna()),
            np.round((df["ebitda_cr"] / df["revenue_cr"]) * 100.0, 2),
            np.nan
        )

        df["net_profit_margin_pct"] = np.where(
            (df["revenue_cr"].notna()) & (df["revenue_cr"] > 0) & (df["pat_cr"].notna()),
            np.round((df["pat_cr"] / df["revenue_cr"]) * 100.0, 2),
            np.nan
        )

        df["debt_to_equity"] = np.where(
            (df["total_debt_cr"].notna()) & (df["net_worth_cr"].notna()) & (df["net_worth_cr"] > 0),
            np.round(df["total_debt_cr"] / df["net_worth_cr"], 2),
            np.nan
        )

        df["prev_revenue_cr"] = df.groupby("company_id")["revenue_cr"].shift(1)
        df["revenue_growth_yoy_pct"] = np.where(
            (df["prev_revenue_cr"].notna()) & (df["prev_revenue_cr"] > 0) & (df["revenue_cr"].notna()),
            np.round(((df["revenue_cr"] / df["prev_revenue_cr"]) - 1.0) * 100.0, 2),
            np.nan
        )

        return df

    def run_cleaning_audit(self) -> Dict[str, Any]:
        """Perform data validation audit across companies, CINs, and financial data."""
        conn = get_connection(self.db_path)
        comp_df = pd.read_sql_query("SELECT * FROM companies", conn)
        conn.close()

        total_companies = len(comp_df)
        valid_cins = sum(self.validate_cin(c) for c in comp_df["cin"])
        has_website = sum(bool(self.clean_website(w)) for w in comp_df["website"])
        
        comp_df["norm_name"] = comp_df["canonical_name"].apply(self.normalize_company_name)
        duplicate_names = comp_df[comp_df.duplicated(subset=["norm_name"], keep=False)]

        audit_results = {
            "total_companies": total_companies,
            "valid_cins": valid_cins,
            "cin_completion_pct": round((valid_cins / total_companies) * 100, 1) if total_companies else 0,
            "has_website": has_website,
            "duplicate_entities_count": len(duplicate_names),
            "unresolved_duplicates": list(duplicate_names["canonical_name"].unique())
        }
        logger.info(f"Cleaning Audit Results: {audit_results}")
        return audit_results

if __name__ == "__main__":
    cleaner = DataCleaner()
    audit = cleaner.run_cleaning_audit()
    print("Audit:", audit)

