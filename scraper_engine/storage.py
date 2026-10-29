import json
import logging
from typing import Dict, Any, Optional
from scraper_engine.db import get_connection

logger = logging.getLogger(__name__)

class StorageManager:
    def __init__(self):
        pass

    def record_source(self, url: str, doc_title: str, source_type: str, http_status: int = 200, cached_path: str = None) -> int:
        """Insert or retrieve source record in sources table."""
        conn = get_connection()
        row = conn.execute("SELECT source_id FROM sources WHERE url = ?", (url,)).fetchone()
        if row:
            source_id = row[0]
            conn.close()
            return source_id

        cur = conn.execute(
            """
            INSERT INTO sources (url, document_title, source_type, http_status, cached_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (url, doc_title or url, source_type, http_status, cached_path)
        )
        source_id = cur.lastrowid
        conn.commit()
        conn.close()
        return source_id

    def store_extracted_data(self, extracted: Dict[str, Any], source_id: int) -> Optional[int]:
        """Store company master, evidence, facilities, financials, and ownership in database."""
        companies = extracted.get("companies", [])
        if not companies:
            return None

        conn = get_connection()
        company_data = companies[0]
        
        cin = company_data.get("cin")
        canonical_name = company_data.get("canonical_name", "").strip()
        existing_company_id = None

        if cin:
            row = conn.execute("SELECT company_id, canonical_name, aliases FROM companies WHERE cin = ?", (cin,)).fetchone()
            if row:
                existing_company_id = row[0]
        
        if not existing_company_id and canonical_name:
            row = conn.execute("SELECT company_id, cin, aliases FROM companies WHERE LOWER(canonical_name) = LOWER(?)", (canonical_name,)).fetchone()
            if row:
                existing_company_id = row[0]

        if existing_company_id:
            company_id = existing_company_id
            conn.execute(
                """
                UPDATE companies
                SET website = COALESCE(website, ?),
                    cin = COALESCE(cin, ?),
                    registered_state = COALESCE(registered_state, ?),
                    registered_office_address = COALESCE(registered_office_address, ?),
                    contact_email = COALESCE(contact_email, ?),
                    all_segments = COALESCE(all_segments, ?),
                    updated_at = CURRENT_TIMESTAMP
                WHERE company_id = ?
                """,
                (
                    company_data.get("website"),
                    cin,
                    company_data.get("registered_state"),
                    company_data.get("registered_office_address"),
                    company_data.get("contact_email"),
                    json.dumps(company_data.get("all_segments", [])),
                    company_id
                )
            )
        else:
            cur = conn.execute(
                """
                INSERT INTO companies (
                    canonical_name, aliases, cin, listing_status, stock_ticker, website,
                    primary_segment, all_segments, business_description, registered_office_address,
                    registered_state, contact_email, contact_phone, confidence_rating
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    canonical_name,
                    company_data.get("aliases"),
                    cin,
                    company_data.get("listing_status", "Unlisted"),
                    company_data.get("stock_ticker"),
                    company_data.get("website"),
                    company_data.get("primary_segment", "general_coatings"),
                    json.dumps(company_data.get("all_segments", [])),
                    company_data.get("business_description"),
                    company_data.get("registered_office_address"),
                    company_data.get("registered_state"),
                    company_data.get("contact_email"),
                    company_data.get("contact_phone"),
                    "High" if cin else "Medium"
                )
            )
            company_id = cur.lastrowid

        evidence_id_map = {}
        for ev in extracted.get("evidence", []):
            cur = conn.execute(
                """
                INSERT INTO evidence (
                    company_id, source_id, claim_type, extracted_fact,
                    exact_text_excerpt, page_or_section, confidence_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    source_id,
                    ev.get("claim_type", "IDENTITY"),
                    ev.get("extracted_fact", ""),
                    ev.get("exact_text_excerpt", "")[:1000],
                    ev.get("page_or_section", "Document"),
                    ev.get("confidence_level", "DIRECT_FACT")
                )
            )
            evidence_id = cur.lastrowid
            evidence_id_map[ev.get("claim_type")] = evidence_id

        for fin in extracted.get("financials", []):
            fin_ev_id = evidence_id_map.get("FINANCIAL")
            conn.execute(
                """
                INSERT INTO financial_observations (
                    company_id, source_id, evidence_id, financial_year, metric_name,
                    metric_value, original_units, value_in_inr_crore, reporting_type,
                    audit_status, page_or_section, text_excerpt
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    source_id,
                    fin_ev_id,
                    fin.get("financial_year", "FY2024-25"),
                    fin.get("metric_name", "REVENUE"),
                    fin.get("metric_value"),
                    fin.get("original_units", "INR Crore"),
                    fin.get("value_in_inr_crore"),
                    fin.get("reporting_type", "STANDALONE"),
                    fin.get("audit_status", "REPORTED"),
                    fin.get("page_or_section"),
                    fin.get("text_excerpt", "")[:1000]
                )
            )

        for fac in extracted.get("facilities", []):
            fac_ev_id = evidence_id_map.get("FACILITY")
            conn.execute(
                """
                INSERT INTO facilities (
                    company_id, source_id, evidence_id, facility_type, facility_address,
                    city, state, industrial_area, stated_capacity, land_ownership, evidence_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    source_id,
                    fac_ev_id,
                    fac.get("facility_type", "MANUFACTURING_PLANT"),
                    fac.get("facility_address", ""),
                    fac.get("city"),
                    fac.get("state"),
                    fac.get("industrial_area"),
                    fac.get("stated_capacity"),
                    fac.get("land_ownership", "UNKNOWN"),
                    fac.get("evidence_text", "")[:1000]
                )
            )

        for own in extracted.get("ownership", []):
            own_ev_id = evidence_id_map.get("OWNERSHIP")
            conn.execute(
                """
                INSERT INTO ownership_observations (
                    company_id, source_id, evidence_id, owner_name, owner_type,
                    holding_percentage, as_of_date, is_controlling, evidence_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    company_id,
                    source_id,
                    own_ev_id,
                    own.get("owner_name", ""),
                    own.get("owner_type", "PROMOTER_INDIVIDUAL"),
                    own.get("holding_percentage"),
                    own.get("as_of_date", "FY2024-25"),
                    own.get("is_controlling", 1),
                    own.get("evidence_text", "")[:1000]
                )
            )

        conn.commit()
        conn.close()
        return company_id
