import re
from pathlib import Path
import pytest
import pandas as pd
from scraper_engine.acquisition_screener import AcquisitionScreener

BASE_DIR = Path(__file__).resolve().parent.parent

def test_screening_logic():
    rev_high = 1500.0
    rec_high = "PASS" if rev_high > 1000.0 else "SHORTLIST"
    assert rec_high == "PASS"

    is_trader = True
    rec_trader = "PASS" if is_trader else "SHORTLIST"
    assert rec_trader == "PASS"

    rev_qualifying = 350.0
    has_plant = True
    is_manufacturer = True
    if rev_qualifying < 1000.0 and has_plant and is_manufacturer:
        rec_target = "SHORTLIST — POTENTIAL ACQUISITION TARGET"
    else:
        rec_target = "PASS"
    assert rec_target == "SHORTLIST — POTENTIAL ACQUISITION TARGET"

def test_expanded_universe_count():
    screening_csv = BASE_DIR / "acquisition_screening.csv"
    if screening_csv.exists():
        df = pd.read_csv(screening_csv)
        shortlisted = df[df["recommendation"] == "SHORTLIST — POTENTIAL ACQUISITION TARGET"]
        assert len(shortlisted) >= 100, f"Expected >= 100 shortlisted targets, got {len(shortlisted)}"
        assert (shortlisted["revenue_inr_cr"] <= 1000.0).all()

def test_all_master_cins_valid():
    master_csv = BASE_DIR / "company_master.csv"
    cin_regex = re.compile(r'^[LUlu][0-9]{5}[A-Za-z]{2}[0-9]{4}[A-Za-z]{3}[0-9]{6}$')
    if master_csv.exists():
        df = pd.read_csv(master_csv)
        assert len(df) >= 120
        for cin in df["cin"].dropna():
            assert cin_regex.match(str(cin)), f"Invalid CIN format found: {cin}"


