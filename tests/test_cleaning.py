import pytest
import pandas as pd
import numpy as np
from scraper_engine.data_cleaning import DataCleaner

def test_normalize_company_name():
    assert DataCleaner.normalize_company_name("Sirca Paints India Ltd") == "Sirca Paints India Limited"
    assert DataCleaner.normalize_company_name("Grand  Polycoats  Company   Pvt. Ltd.") == "Grand Polycoats Company Private Limited"
    assert DataCleaner.normalize_company_name("Asian Paints Limited") == "Asian Paints Limited"

def test_validate_cin():
    assert DataCleaner.validate_cin("L24219DL2006PLC145092") is True
    assert DataCleaner.validate_cin("U24222GJ1981PTC004456") is True
    assert DataCleaner.validate_cin("INVALID_CIN_123") is False
    assert DataCleaner.validate_cin(None) is False

def test_normalize_state():
    assert DataCleaner.normalize_state("MH") == "Maharashtra"
    assert DataCleaner.normalize_state("gujarat") == "Gujarat"
    assert DataCleaner.normalize_state("TN") == "Tamil Nadu"
    assert DataCleaner.normalize_state("New Delhi") == "Delhi"
    assert DataCleaner.normalize_state("KL") == "Kerala"
    assert DataCleaner.normalize_state("MP") == "Madhya Pradesh"

def test_financial_ratio_calculations():
    sample_df = pd.DataFrame([
        {"company_id": 1, "financial_year": "FY2023-24", "revenue_cr": 100.0, "ebitda_cr": 20.0, "pat_cr": 10.0, "total_debt_cr": 25.0, "net_worth_cr": 50.0},
        {"company_id": 1, "financial_year": "FY2024-25", "revenue_cr": 125.0, "ebitda_cr": 30.0, "pat_cr": 15.0, "total_debt_cr": 20.0, "net_worth_cr": 65.0}
    ])
    
    sample_df["ebitda_margin_pct"] = (sample_df["ebitda_cr"] / sample_df["revenue_cr"]) * 100.0
    sample_df["net_profit_margin_pct"] = (sample_df["pat_cr"] / sample_df["revenue_cr"]) * 100.0
    sample_df["debt_to_equity"] = sample_df["total_debt_cr"] / sample_df["net_worth_cr"]
    sample_df["prev_revenue_cr"] = sample_df["revenue_cr"].shift(1)
    sample_df["revenue_growth_yoy_pct"] = ((sample_df["revenue_cr"] / sample_df["prev_revenue_cr"]) - 1.0) * 100.0

    assert sample_df.loc[0, "ebitda_margin_pct"] == 20.0
    assert sample_df.loc[1, "ebitda_margin_pct"] == 24.0
    assert sample_df.loc[0, "debt_to_equity"] == 0.5
    assert sample_df.loc[1, "revenue_growth_yoy_pct"] == 25.0

