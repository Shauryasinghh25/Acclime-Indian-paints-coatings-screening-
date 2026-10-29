import pytest
from scraper_engine.extractor import Extractor, CIN_REGEX, FINANCIAL_PATTERNS

def test_cin_regex():
    sample_text = "The company is registered under CIN L24219DL2006PLC145092 with ROC Delhi."
    cins = CIN_REGEX.findall(sample_text)
    assert len(cins) == 1
    assert cins[0] == "L24219DL2006PLC145092"

def test_financial_extraction_patterns():
    sample_ptext = "During FY 2024-25, revenue from operations was Rs. 311.5 crore. Operating profit stood at Rs. 69.2 crore while profit after tax was Rs. 51.0 crore."
    extractor = Extractor()
    financials = extractor._detect_financials(sample_ptext, "https://sample.com")
    
    metrics = {f["metric_name"]: f["value_in_inr_crore"] for f in financials}
    assert "REVENUE" in metrics
    assert metrics["REVENUE"] == 311.5
    assert "EBITDA" in metrics
    assert metrics["EBITDA"] == 69.2
    assert "PAT" in metrics
    assert metrics["PAT"] == 51.0

def test_html_extraction():
    html = b"""
    <html>
        <head><title>Grand Polycoats Company Pvt Ltd</title></head>
        <body>
            <p>CIN: U24222GJ1981PTC004456</p>
            <p>We manufacture heavy duty protective coating, epoxy primer, and polyurethane systems.</p>
            <p>Factory works at Padra, GIDC Vadodara, Gujarat with capacity of 15,000 MTPA.</p>
        </body>
    </html>
    """
    extractor = Extractor()
    res = extractor.extract_from_html(html, "https://www.grandpolycoats.com")
    assert len(res["companies"]) == 1
    comp = res["companies"][0]
    assert comp["cin"] == "U24222GJ1981PTC004456"
    assert "protective_marine" in comp["all_segments"]
    assert len(res["facilities"]) >= 1

