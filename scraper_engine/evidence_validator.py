import logging
import pandas as pd
from typing import Dict, Any, List
from scraper_engine.db import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("evidence_validator")

class EvidenceValidator:
    def __init__(self, db_path: str = None):
        self.db_path = db_path

    def get_full_evidence_register(self) -> pd.DataFrame:
        """Fetch unified field-level evidence register across companies, sources, and evidence claims."""
        conn = get_connection(self.db_path)
        query = """
        SELECT
            e.evidence_id,
            e.company_id,
            c.canonical_name as company_name,
            c.cin,
            e.claim_type,
            e.extracted_fact as claim_fact,
            e.page_or_section,
            e.verification_status,
            e.confidence_level,
            e.exact_text_excerpt,
            s.url as source_url,
            s.document_title as source_title,
            s.source_type,
            s.retrieval_date,
            e.created_at as evidence_logged_at
        FROM evidence e
        JOIN companies c ON e.company_id = c.company_id
        JOIN sources s ON e.source_id = s.source_id
        ORDER BY e.company_id, e.claim_type, e.evidence_id ASC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        logger.info(f"Retrieved {len(df)} traceable evidence register records.")
        return df

    def validate_traceability(self) -> Dict[str, Any]:
        """Verify that 100% of material claims possess source URLs and valid verification status."""
        df = self.get_full_evidence_register()
        if df.empty:
            return {"total_evidence_records": 0, "traceability_pct": 0.0, "status_breakdown": {}}

        total = len(df)
        with_url = df["source_url"].notna().sum()
        with_excerpt = (df["exact_text_excerpt"].str.len() > 10).sum()
        status_breakdown = df["verification_status"].value_counts().to_dict()

        return {
            "total_evidence_records": total,
            "with_valid_source_url": int(with_url),
            "with_exact_text_excerpt": int(with_excerpt),
            "traceability_pct": round((with_url / total) * 100.0, 1),
            "verification_status_breakdown": status_breakdown
        }

if __name__ == "__main__":
    validator = EvidenceValidator()
    print("Traceability report:", validator.validate_traceability())

