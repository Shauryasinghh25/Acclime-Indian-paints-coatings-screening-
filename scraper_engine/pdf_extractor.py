import io
import re
import logging
from typing import Dict, Any, List, Optional
import pdfplumber
from scraper_engine.extractor import CIN_REGEX, FINANCIAL_PATTERNS, SEGMENT_KEYWORDS

logger = logging.getLogger("pdf_extractor")

class PDFExtractor:
    """Extracts tables, financial metrics, facilities, and evidence from annual reports & credit rating rationales."""

    def __init__(self):
        pass

    def extract_from_pdf_bytes(self, pdf_bytes: bytes, filename_or_url: str) -> Dict[str, Any]:
        results = {
            "source": filename_or_url,
            "cin": None,
            "financials": [],
            "facilities": [],
            "segments_detected": set(),
            "full_text_pages": []
        }

        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for idx, page in enumerate(pdf.pages[:20]):
                    p_text = page.extract_text() or ""
                    results["full_text_pages"].append((idx + 1, p_text))

                    if not results["cin"]:
                        cins = CIN_REGEX.findall(p_text)
                        if cins:
                            results["cin"] = cins[0]

                    for pat, metric in FINANCIAL_PATTERNS:
                        for m in re.finditer(pat, p_text, re.IGNORECASE):
                            val_str, unit = m.group(1), m.group(2)
                            try:
                                val = float(val_str.replace(",", ""))
                            except ValueError:
                                continue

                            val_cr = val if "cr" in unit.lower() else val / 100.0 if "lakh" in unit.lower() else val / 10.0
                            context_start = max(0, m.start() - 80)
                            context_end = min(len(p_text), m.end() + 80)
                            excerpt = p_text[context_start:context_end].replace("\n", " ").strip()

                            results["financials"].append({
                                "metric_name": metric,
                                "metric_value": val,
                                "value_in_inr_crore": round(val_cr, 2),
                                "unit": unit,
                                "page": idx + 1,
                                "excerpt": excerpt
                            })

                    p_lower = p_text.lower()
                    for seg, kw_list in SEGMENT_KEYWORDS.items():
                        if any(kw in p_lower for kw in kw_list):
                            results["segments_detected"].add(seg)

            results["segments_detected"] = list(results["segments_detected"])
            logger.info(f"PDF extraction complete for {filename_or_url}: found {len(results['financials'])} metric points.")
            return results

        except Exception as e:
            logger.error(f"Error parsing PDF {filename_or_url}: {e}")
            return results

