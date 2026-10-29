import re
import io
import logging
from typing import Dict, Any, List, Optional, Tuple
from bs4 import BeautifulSoup
import pdfplumber

logger = logging.getLogger(__name__)

CIN_REGEX = re.compile(r'\b([LUlu][0-9]{5}[A-Za-z]{2}[0-9]{4}[A-Za-z]{3}[0-9]{6})\b')
PAN_REGEX = re.compile(r'\b([A-Za-z]{5}[0-9]{4}[A-Za-z]{1})\b')
PINCODE_REGEX = re.compile(r'\b([1-9][0-9]{2}\s?[0-9]{3})\b')

FINANCIAL_PATTERNS = [
    (
        r'(?:total\s+operating\s+income|operating\s+income|revenue\s+from\s+operations|net\s+sales|turnover|revenue)\s*(?:of|was|stood\s+at|reached|touched)?\s*(?:rs\.?|inr|₹)?\s*([0-9]+(?:\.[0-9]+)?)\s*(crore|cr|lakh|lakhs|million|mn|billion|bn)',
        "REVENUE"
    ),
    (
        r'(?:ebitda|operating\s+profit)\s*(?:of|was|stood\s+at)?\s*(?:rs\.?|inr|₹)?\s*([0-9]+(?:\.[0-9]+)?)\s*(crore|cr|lakh|lakhs|million|mn)',
        "EBITDA"
    ),
    (
        r'(?:profit\s+after\s+tax|pat|net\s+profit|net\s+loss)\s*(?:of|was|stood\s+at)?\s*(?:rs\.?|inr|₹)?\s*(-?[0-9]+(?:\.[0-9]+)?)\s*(crore|cr|lakh|lakhs|million|mn)',
        "PAT"
    ),
    (
        r'(?:net\s+worth|tangible\s+net\s+worth)\s*(?:of|was|stood\s+at)?\s*(?:rs\.?|inr|₹)?\s*([0-9]+(?:\.[0-9]+)?)\s*(crore|cr|lakh|lakhs|million|mn)',
        "NET_WORTH"
    ),
    (
        r'(?:total\s+debt|borrowings|total\s+external\s+debt)\s*(?:of|was|stood\s+at)?\s*(?:rs\.?|inr|₹)?\s*([0-9]+(?:\.[0-9]+)?)\s*(crore|cr|lakh|lakhs|million|mn)',
        "TOTAL_DEBT"
    )
]

YEAR_REGEX = re.compile(r'\b(FY\s*20?2[0-9](?:-[0-9]{2,4})?|202[0-9]-2[0-9]|fiscal\s*202[0-9](?:-[0-9]{2,4})?|FY2[0-9](?:-[0-9]{2})?)\b', re.IGNORECASE)

SEGMENT_KEYWORDS = {
    "decorative": ["decorative", "emulsion", "distemper", "wall putty", "exterior paint", "interior paint", "architectural paint", "cement paint"],
    "industrial": ["industrial paint", "industrial coating", "stoving enamel", "polyurethane paint", "epoxy primer", "machinery coating"],
    "powder": ["powder coating", "powder paints", "thermosetting powder", "epoxy polyester", "pure polyester powder"],
    "protective_marine": ["protective coating", "marine paint", "anti-corrosive", "heavy duty coating", "polyurea", "epoxy coating", "zinc silicate"],
    "wood": ["wood finish", "wood polish", "polyurethane wood", "melamine", "nc lacquer", "italian wood", "wood coating"],
    "automotive": ["automotive paint", "auto refinish", "auto oem", "car paint", "2k clear", "vehicle coating"],
    "coil": ["coil coating", "pre-coated metal", "strip coating", "can coating"],
    "specialty_resins": ["synthetic resin", "alkyd resin", "unsaturated polyester resin", "vinyl ester", "gelcoat", "phenolic resin"]
}

FACILITY_KEYWORDS = [
    "plant", "factory", "manufacturing unit", "manufacturing facility", "works", "production facility",
    "midc", "gidc", "hsiidc", "sipcot", "sidco", "industrial estate", "industrial area", "industrial park"
]

class Extractor:
    def __init__(self):
        pass

    def extract_from_html(self, html_bytes: bytes, url: str) -> Dict[str, Any]:
        """Parse HTML page and extract company data, facilities, evidence and financials."""
        try:
            soup = BeautifulSoup(html_bytes, "html.parser")
        except Exception as e:
            logger.error(f"HTML parse error for {url}: {e}")
            return {}

        for elem in soup(["script", "style", "noscript", "svg"]):
            elem.decompose()

        page_title = soup.title.string.strip() if soup.title and soup.title.string else ""
        text = soup.get_text(separator="\n", strip=True)
        text_lower = text.lower()

        extracted: Dict[str, Any] = {
            "source_type": "WEBSITE_HTML",
            "document_title": page_title,
            "url": url,
            "companies": [],
            "evidence": [],
            "financials": [],
            "facilities": [],
            "ownership": []
        }

        cins = list(set(CIN_REGEX.findall(text)))
        cin = cins[0] if cins else None

        company_name = self._detect_company_name(soup, page_title, text)
        if not company_name and not cin:
            return extracted

        detected_segments = []
        for segment, keywords in SEGMENT_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                detected_segments.append(segment)

        address_info = self._detect_address(soup, text)

        facilities = self._detect_facilities(soup, text)

        financials = self._detect_financials(text, url)

        ownership = self._detect_ownership(text)

        company_record = {
            "canonical_name": company_name or "Unknown Company",
            "aliases": self._detect_aliases(company_name, text),
            "cin": cin,
            "website": self._clean_website(url),
            "listing_status": self._detect_listing_status(text),
            "primary_segment": detected_segments[0] if detected_segments else "general_coatings",
            "all_segments": detected_segments,
            "business_description": self._extract_meta_description(soup) or text[:300].strip(),
            "registered_office_address": address_info.get("address"),
            "registered_state": address_info.get("state"),
            "contact_email": self._extract_email(text),
            "contact_phone": self._extract_phone(text)
        }
        extracted["companies"].append(company_record)

        if cin:
            extracted["evidence"].append({
                "claim_type": "IDENTITY",
                "extracted_fact": f"CIN: {cin}",
                "exact_text_excerpt": self._get_context_snippet(text, cin),
                "page_or_section": "Footer / Legal",
                "confidence_level": "DIRECT_FACT"
            })

        for seg in detected_segments:
            sample_kw = next(kw for kw in SEGMENT_KEYWORDS[seg] if kw in text_lower)
            extracted["evidence"].append({
                "claim_type": "PRODUCT",
                "extracted_fact": f"Produces {seg} ({sample_kw})",
                "exact_text_excerpt": self._get_context_snippet(text, sample_kw),
                "page_or_section": "Products / Overview",
                "confidence_level": "DIRECT_FACT"
            })

        for fac in facilities:
            extracted["facilities"].append(fac)
            extracted["evidence"].append({
                "claim_type": "FACILITY",
                "extracted_fact": f"Facility at {fac.get('facility_address')}",
                "exact_text_excerpt": fac.get("evidence_text", ""),
                "page_or_section": "Contact / Manufacturing",
                "confidence_level": "DIRECT_FACT"
            })

        for fin in financials:
            extracted["financials"].append(fin)
            extracted["evidence"].append({
                "claim_type": "FINANCIAL",
                "extracted_fact": f"{fin.get('financial_year')} {fin.get('metric_name')}: {fin.get('metric_value')} {fin.get('original_units')}",
                "exact_text_excerpt": fin.get("text_excerpt", ""),
                "page_or_section": "Financial Disclosures",
                "confidence_level": "DIRECT_FACT"
            })

        for own in ownership:
            extracted["ownership"].append(own)
            extracted["evidence"].append({
                "claim_type": "OWNERSHIP",
                "extracted_fact": f"Owner/Promoter: {own.get('owner_name')}",
                "exact_text_excerpt": own.get("evidence_text", ""),
                "page_or_section": "About / Governance",
                "confidence_level": "VERIFIED_LEAD"
            })

        return extracted

    def extract_from_pdf(self, pdf_bytes: bytes, url: str) -> Dict[str, Any]:
        """Parse PDF document (rating rationale, annual report) via pdfplumber."""
        extracted: Dict[str, Any] = {
            "source_type": "PDF_REPORT",
            "document_title": url.split("/")[-1],
            "url": url,
            "companies": [],
            "evidence": [],
            "financials": [],
            "facilities": [],
            "ownership": []
        }

        try:
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                full_text = []
                for idx, page in enumerate(pdf.pages[:15]):
                    page_text = page.extract_text() or ""
                    full_text.append((idx + 1, page_text))
        except Exception as e:
            logger.error(f"PDF extraction error for {url}: {e}")
            return extracted

        combined_text = " ".join([pt[1] for pt in full_text])
        if not combined_text.strip():
            return extracted

        cins = list(set(CIN_REGEX.findall(combined_text)))
        cin = cins[0] if cins else None

        company_name = self._detect_company_name_from_text(combined_text)

        for page_num, ptext in full_text:
            page_financials = self._detect_financials(ptext, url, page_num=f"Page {page_num}")
            for fin in page_financials:
                extracted["financials"].append(fin)
                extracted["evidence"].append({
                    "claim_type": "FINANCIAL",
                    "extracted_fact": f"{fin.get('financial_year')} {fin.get('metric_name')}: {fin.get('metric_value')} {fin.get('original_units')}",
                    "exact_text_excerpt": fin.get("text_excerpt", ""),
                    "page_or_section": f"Page {page_num}",
                    "confidence_level": "DIRECT_FACT"
                })

        detected_segments = []
        text_lower = combined_text.lower()
        for segment, keywords in SEGMENT_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                detected_segments.append(segment)

        facilities = self._detect_facilities_from_text(combined_text)
        for fac in facilities:
            extracted["facilities"].append(fac)
            extracted["evidence"].append({
                "claim_type": "FACILITY",
                "extracted_fact": f"Plant at {fac.get('facility_address')}",
                "exact_text_excerpt": fac.get("evidence_text", ""),
                "page_or_section": "Rating Rationale / Profile",
                "confidence_level": "DIRECT_FACT"
            })

        if company_name or cin:
            extracted["companies"].append({
                "canonical_name": company_name or "Discovered Entity",
                "aliases": self._detect_aliases(company_name, combined_text),
                "cin": cin,
                "website": "",
                "listing_status": self._detect_listing_status(combined_text),
                "primary_segment": detected_segments[0] if detected_segments else "general_coatings",
                "all_segments": detected_segments,
                "business_description": combined_text[:400].strip(),
                "registered_office_address": "",
                "registered_state": self._detect_state_from_text(combined_text),
                "contact_email": self._extract_email(combined_text),
                "contact_phone": ""
            })

        return extracted

    def _detect_company_name(self, soup: BeautifulSoup, title: str, text: str) -> Optional[str]:
        meta_site = soup.find("meta", property="og:site_name")
        if meta_site and meta_site.get("content"):
            name = meta_site.get("content").strip()
            if len(name) > 3 and not any(skip in name.lower() for skip in ["home", "welcome", "page"]):
                return name

        copyright_pattern = re.compile(r'(?:copyright|©)\s*(?:[0-9]{4})?\s*([A-Za-z0-9\s\.\,\(\)\-]+?(?:pvt\.?\s*ltd\.?|private\s+limited|limited|ltd\.?))', re.IGNORECASE)
        match = copyright_pattern.search(text)
        if match:
            clean = match.group(1).strip()
            if len(clean) > 4:
                return clean

        if title:
            parts = re.split(r'[\-\|\:\–]', title)
            first_part = parts[0].strip()
            if any(term in first_part.lower() for term in ["paint", "coating", "chemical", "poly", "varnish", "resin", "industries", "ltd"]):
                return first_part

        return self._detect_company_name_from_text(text)

    def _detect_company_name_from_text(self, text: str) -> Optional[str]:
        name_pattern = re.compile(r'\b([A-Z][A-Za-z0-9\s\.\&\-]{2,40}\s+(?:Private\s+Limited|Pvt\.?\s*Ltd\.?|Limited|Ltd\.?))\b')
        matches = name_pattern.findall(text)
        if matches:
            counts = {m: matches.count(m) for m in set(matches) if not m.lower().startswith("copyright")}
            if counts:
                return max(counts, key=counts.get).strip()
        return None

    def _detect_aliases(self, company_name: Optional[str], text: str) -> Optional[str]:
        if not company_name:
            return None
        short = re.sub(r'\s+(?:Private\s+Limited|Pvt\.?\s*Ltd\.?|Limited|Ltd\.?)', '', company_name, flags=re.IGNORECASE).strip()
        if short != company_name:
            return short
        return None

    def _detect_address(self, soup: BeautifulSoup, text: str) -> Dict[str, Optional[str]]:
        addr_tag = soup.find("address")
        addr_text = addr_tag.get_text(separator=" ", strip=True) if addr_tag else ""
        if not addr_text:
            match = re.search(r'(?:registered\s+office|head\s+office|corporate\s+office)\s*[:\-]?\s*([^.]+?(?:[1-9][0-9]{2}\s?[0-9]{3}))', text, re.IGNORECASE)
            if match:
                addr_text = match.group(0).strip()

        state = self._detect_state_from_text(addr_text or text)
        return {"address": addr_text if len(addr_text) > 10 else None, "state": state}

    def _detect_state_from_text(self, text: str) -> Optional[str]:
        states = ["Maharashtra", "Gujarat", "Haryana", "Tamil Nadu", "Uttar Pradesh", "West Bengal", "Karnataka", "Telangana", "Rajasthan", "Punjab", "Andhra Pradesh", "Goa", "Delhi", "Kerala"]
        text_lower = text.lower()
        for st in states:
            if st.lower() in text_lower:
                return st
        return None

    def _detect_facilities(self, soup: BeautifulSoup, text: str) -> List[Dict[str, Any]]:
        facilities = []
        blocks = [line.strip() for line in text.splitlines() if line.strip()]
        if len(blocks) < 3:
            sentence_pattern = re.compile(r'(?<!\d)(?<!\bNo)(?<!\bLtd)(?<!\bPvt)(?<!\bCo)(?<!\bMr)(?<!\bMs)\.\s+(?=[A-Z0-9])')
            blocks = sentence_pattern.split(text)

        global_capacity = self._extract_capacity(text)

        for b in blocks:
            b_clean = b.strip()
            if any(kw in b_clean.lower() for kw in FACILITY_KEYWORDS):
                if len(b_clean) > 25 and len(b_clean) < 800:
                    city, state, area = self._parse_facility_location(b_clean)
                    cap = self._extract_capacity(b_clean) or global_capacity
                    facilities.append({
                        "facility_type": "MANUFACTURING_PLANT",
                        "facility_address": b_clean,
                        "city": city,
                        "state": state,
                        "industrial_area": area,
                        "stated_capacity": cap,
                        "evidence_text": b_clean
                    })
                    if len(facilities) >= 3:
                        break
        return facilities

    def _detect_facilities_from_text(self, text: str) -> List[Dict[str, Any]]:
        return self._detect_facilities(BeautifulSoup("", "html.parser"), text)

    def _parse_facility_location(self, text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        state = self._detect_state_from_text(text)
        area_match = re.search(r'\b(MIDC|GIDC|HSIIDC|SIPCOT|RIICO|Industrial\s+Area|Industrial\s+Estate)\b', text, re.IGNORECASE)
        area = area_match.group(0) if area_match else None
        
        common_cities = ["Pune", "Vadodara", "Sonipat", "Sahibabad", "Chennai", "Bhiwadi", "Ambernath", "Taloja", "Nashik", "Ranipet", "Padra", "Kheda", "Dharwad", "Bengaluru", "Faridabad", "Thane"]
        city = None
        for c in common_cities:
            if c.lower() in text.lower():
                city = c
                break
        return city, state, area

    def _extract_capacity(self, text: str) -> Optional[str]:
        match = re.search(r'([0-9,]+(?:\.[0-9]+)?\s*(?:mtpa|tonnes|metric\s+tons|kl|kilolitres|litres)\s*(?:per\s+annum|\/annum|\/yr)?)', text, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _detect_financials(self, text: str, url: str, page_num: str = "HTML Page") -> List[Dict[str, Any]]:
        obs = []
        for pat, metric in FINANCIAL_PATTERNS:
            regex = re.compile(pat, re.IGNORECASE)
            for m in regex.finditer(text):
                val_str, unit = m.group(1), m.group(2)
                try:
                    val = float(val_str.replace(",", ""))
                except ValueError:
                    continue

                start = max(0, m.start() - 100)
                end = min(len(text), m.end() + 100)
                context = text[start:end]
                
                yr_match = YEAR_REGEX.search(context)
                fin_year = yr_match.group(1).upper() if yr_match else "FY2024-25"
                
                unit_norm = "INR Crore" if "cr" in unit.lower() else "INR Lakhs" if "lakh" in unit.lower() else "INR Million"
                val_cr = val if unit_norm == "INR Crore" else val / 100.0 if unit_norm == "INR Lakhs" else val / 10.0

                rep_type = "CONSOLIDATED" if "consolidated" in context.lower() else "STANDALONE"

                obs.append({
                    "financial_year": fin_year,
                    "metric_name": metric,
                    "metric_value": val,
                    "original_units": unit_norm,
                    "value_in_inr_crore": round(val_cr, 2),
                    "reporting_type": rep_type,
                    "audit_status": "AUDITED" if "audited" in context.lower() else "REPORTED",
                    "page_or_section": page_num,
                    "text_excerpt": context.strip()
                })
        return obs

    def _detect_ownership(self, text: str) -> List[Dict[str, Any]]:
        owners = []
        match_prom = re.search(r'(?:promoted\s+by|founded\s+by|promoter[s]?\s*[:\-]|chairperson|managing\s+director)\s*[:\-]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})', text)
        if match_prom:
            owners.append({
                "owner_name": match_prom.group(1).strip(),
                "owner_type": "PROMOTER_INDIVIDUAL",
                "holding_percentage": None,
                "as_of_date": "FY2024-25",
                "is_controlling": 1,
                "evidence_text": match_prom.group(0).strip()
            })

        match_sub = re.search(r'(?:wholly[\-\s]owned\s+subsidiary\s+of|subsidiary\s+of|joint\s+venture\s+between)\s*([A-Z][A-Za-z0-9\s\.\&]+?(?:limited|ltd|inc|corp|a\/s|se))', text, re.IGNORECASE)
        if match_sub:
            owners.append({
                "owner_name": match_sub.group(1).strip(),
                "owner_type": "CORPORATE_PARENT",
                "holding_percentage": 100.0 if "wholly" in match_sub.group(0).lower() else None,
                "as_of_date": "FY2024-25",
                "is_controlling": 1,
                "evidence_text": match_sub.group(0).strip()
            })
        return owners

    def _detect_listing_status(self, text: str) -> str:
        text_lower = text.lower()
        if "bse sm" in text_lower or "nse sm" in text_lower or "emerge" in text_lower:
            return "Listed SME"
        elif "bse:" in text_lower or "nse:" in text_lower or "scrip code" in text_lower or "isin" in text_lower or "listed on bse" in text_lower or "listed on nse" in text_lower:
            return "Listed"
        return "Unlisted"

    def _clean_website(self, url: str) -> str:
        from urllib.parse import urlparse
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}"

    def _extract_meta_description(self, soup: BeautifulSoup) -> Optional[str]:
        meta = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", property="og:description")
        return meta.get("content").strip() if meta and meta.get("content") else None

    def _extract_email(self, text: str) -> Optional[str]:
        match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        return match.group(0) if match else None

    def _extract_phone(self, text: str) -> Optional[str]:
        match = re.search(r'(?:\+91[\-\s]?)?[0-9]{3,5}[\-\s]?[0-9]{6,8}', text)
        return match.group(0).strip() if match else None

    def _get_context_snippet(self, text: str, target: str, window: int = 80) -> str:
        idx = text.lower().find(target.lower())
        if idx == -1:
            return text[:160].strip()
        start = max(0, idx - window)
        end = min(len(text), idx + len(target) + window)
        return text[start:end].strip()
