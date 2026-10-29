import sqlite3
import os
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "paints_database.db"

def get_connection(db_path: str = None) -> sqlite3.Connection:
    """Return an SQLite connection with WAL mode and foreign keys enabled."""
    target_path = db_path or str(DEFAULT_DB_PATH)
    conn = sqlite3.connect(target_path, timeout=30.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str = None) -> None:
    """Initialize SQLite tables for companies, sources, evidence, financials, facilities, ownership, screening, and logs."""
    conn = get_connection(db_path)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sources (
        source_id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        document_title TEXT,
        source_type TEXT,
        http_status INTEGER DEFAULT 200,
        cached_path TEXT,
        retrieval_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        company_id INTEGER PRIMARY KEY AUTOINCREMENT,
        canonical_name TEXT NOT NULL,
        aliases TEXT,
        cin TEXT UNIQUE,
        listing_status TEXT DEFAULT 'Unlisted',
        stock_ticker TEXT,
        website TEXT,
        primary_segment TEXT,
        all_segments TEXT,
        business_description TEXT,
        registered_office_address TEXT,
        registered_state TEXT,
        city TEXT,
        incorporation_year INTEGER,
        contact_email TEXT,
        contact_phone TEXT,
        manufacturing_status TEXT DEFAULT 'VERIFIED_MANUFACTURER',
        confidence_rating TEXT DEFAULT 'Medium',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS evidence (
        evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        source_id INTEGER,
        claim_type TEXT,
        extracted_fact TEXT,
        exact_text_excerpt TEXT,
        page_or_section TEXT,
        confidence_level TEXT DEFAULT 'DIRECT_FACT',
        verification_status TEXT DEFAULT 'Verified from primary source',
        conflict_notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies(company_id),
        FOREIGN KEY (source_id) REFERENCES sources(source_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS financial_observations (
        fin_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        source_id INTEGER,
        evidence_id INTEGER,
        financial_year TEXT,
        metric_name TEXT,
        metric_value REAL,
        original_units TEXT,
        value_in_inr_crore REAL,
        reporting_type TEXT DEFAULT 'STANDALONE',
        audit_status TEXT DEFAULT 'AUDITED',
        page_or_section TEXT,
        text_excerpt TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies(company_id),
        FOREIGN KEY (source_id) REFERENCES sources(source_id),
        FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS facilities (
        facility_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        source_id INTEGER,
        evidence_id INTEGER,
        facility_name TEXT,
        facility_type TEXT DEFAULT 'MANUFACTURING_PLANT',
        facility_address TEXT,
        city TEXT,
        state TEXT,
        industrial_area TEXT,
        products_manufactured TEXT,
        stated_capacity TEXT,
        actual_production TEXT,
        land_ownership TEXT DEFAULT 'UNKNOWN',
        evidence_text TEXT,
        verification_status TEXT DEFAULT 'Verified from primary source',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies(company_id),
        FOREIGN KEY (source_id) REFERENCES sources(source_id),
        FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ownership_observations (
        ownership_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        source_id INTEGER,
        evidence_id INTEGER,
        owner_name TEXT,
        owner_type TEXT DEFAULT 'PROMOTER_INDIVIDUAL',
        holding_percentage REAL,
        as_of_date TEXT,
        is_controlling INTEGER DEFAULT 1,
        evidence_text TEXT,
        verification_status TEXT DEFAULT 'Verified from primary source',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies(company_id),
        FOREIGN KEY (source_id) REFERENCES sources(source_id),
        FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS discovery_records (
        discovery_id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_name TEXT NOT NULL,
        raw_url TEXT,
        discovery_source TEXT,
        search_category TEXT,
        city TEXT,
        state TEXT,
        initial_classification TEXT,
        status TEXT DEFAULT 'DISCOVERED',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS acquisition_screening (
        screening_id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER UNIQUE,
        revenue_inr_cr REAL,
        financial_year TEXT,
        revenue_eligibility TEXT,
        manufacturing_verification TEXT,
        profitability_summary TEXT,
        financial_risk TEXT,
        strategic_fit TEXT,
        geographic_footprint TEXT,
        ownership_structure TEXT,
        key_risks TEXT,
        recommendation TEXT,
        recommendation_rationale TEXT,
        missing_evidence TEXT,
        confidence_level TEXT,
        source_references TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (company_id) REFERENCES companies(company_id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS scraping_errors (
        error_id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_url TEXT,
        error_type TEXT,
        error_message TEXT,
        retry_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'LOGGED',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DEFAULT_DB_PATH)

