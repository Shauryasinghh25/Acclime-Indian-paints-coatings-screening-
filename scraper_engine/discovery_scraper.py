import logging
import requests
import time
from typing import List, Dict, Any
from scraper_engine.db import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("discovery_scraper")

DISCOVERY_CANDIDATE_CATALOG = [
    {
        "candidate_name": "Sirca Paints India Limited",
        "raw_url": "https://www.screener.in/company/SIRCA/",
        "discovery_source": "Screener.in / NSE",
        "search_category": "wood_coatings",
        "city": "New Delhi",
        "state": "Delhi",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Shalimar Paints Limited",
        "raw_url": "https://www.screener.in/company/SHALPAINTS/consolidated/",
        "discovery_source": "Screener.in / BSE/NSE",
        "search_category": "decorative_industrial",
        "city": "Gurugram",
        "state": "Haryana",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Kamdhenu Ventures Limited",
        "raw_url": "https://www.screener.in/company/KAMOPAINTS/consolidated/",
        "discovery_source": "Screener.in / NSE",
        "search_category": "decorative",
        "city": "Gurugram",
        "state": "Haryana",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Retina Paints Limited",
        "raw_url": "https://www.screener.in/company/543902/",
        "discovery_source": "Screener.in / BSE SME",
        "search_category": "decorative_architectural",
        "city": "Hyderabad",
        "state": "Telangana",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Siddhika Coatings Limited",
        "raw_url": "https://www.screener.in/company/SIDDHIKA/",
        "discovery_source": "Screener.in / NSE Emerge",
        "search_category": "specialty_architectural",
        "city": "New Delhi",
        "state": "Delhi",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Metal Coatings (India) Limited",
        "raw_url": "https://www.screener.in/company/531810/",
        "discovery_source": "Screener.in / BSE",
        "search_category": "coil_and_metal_coatings",
        "city": "Faridabad",
        "state": "Haryana",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Organic Coatings Limited",
        "raw_url": "https://www.screener.in/company/531157/",
        "discovery_source": "Screener.in / BSE",
        "search_category": "specialty_printing_coatings",
        "city": "Mumbai",
        "state": "Maharashtra",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Multilac Surface Coating (I) Limited",
        "raw_url": "https://www.screener.in/company/526763/",
        "discovery_source": "Screener.in / BSE",
        "search_category": "surface_coatings",
        "city": "Mumbai",
        "state": "Maharashtra",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Jyoti Resins and Adhesives Limited",
        "raw_url": "https://www.screener.in/company/JYOTIRES/",
        "discovery_source": "Screener.in / BSE",
        "search_category": "synthetic_resins_coatings",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Sreechem Resins Limited",
        "raw_url": "https://www.screener.in/company/514248/",
        "discovery_source": "Screener.in / BSE",
        "search_category": "specialty_resins_coatings",
        "city": "Kolkata",
        "state": "West Bengal",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "IVP Limited",
        "raw_url": "https://www.screener.in/company/IVP/",
        "discovery_source": "Screener.in / BSE/NSE",
        "search_category": "foundry_coatings_resins",
        "city": "Mumbai",
        "state": "Maharashtra",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Grauer & Weil (India) Limited",
        "raw_url": "https://www.screener.in/company/GRAUWEIL/",
        "discovery_source": "Screener.in / BSE/NSE",
        "search_category": "protective_industrial_coatings",
        "city": "Mumbai",
        "state": "Maharashtra",
        "initial_classification": "MANUFACTURER"
    },

    {
        "candidate_name": "Grand Polycoats Company Private Limited",
        "raw_url": "https://www.grandpolycoats.com",
        "discovery_source": "CRISIL Rating / ZaubaCorp",
        "search_category": "heavy_duty_protective_marine",
        "city": "Vadodara",
        "state": "Gujarat",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Sheenlac Paints Limited",
        "raw_url": "https://www.sheenlac.com",
        "discovery_source": "CRISIL Rating / The Company Check",
        "search_category": "decorative_wood_coatings",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Surfa Coats (India) Private Limited",
        "raw_url": "https://www.surfacoatspaints.in",
        "discovery_source": "MCA / ZaubaCorp / Directory",
        "search_category": "decorative_architectural",
        "city": "Bengaluru",
        "state": "Karnataka",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Coatings and Coatings (India) Private Limited",
        "raw_url": "https://www.crisilratings.com",
        "discovery_source": "CRISIL Ratings",
        "search_category": "industrial_wood_coatings",
        "city": "Mumbai",
        "state": "Maharashtra",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Marpol Private Limited",
        "raw_url": "https://www.marpol.com",
        "discovery_source": "Industry Directory / IPCA",
        "search_category": "powder_coatings",
        "city": "Ponda",
        "state": "Goa",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Advance Paints Private Limited",
        "raw_url": "https://www.advancepaints.com",
        "discovery_source": "Industry Directory / ZaubaCorp",
        "search_category": "industrial_protective_coatings",
        "city": "Mumbai",
        "state": "Maharashtra",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Apollo Paints Private Limited",
        "raw_url": "https://www.apollopaints.com",
        "discovery_source": "ZaubaCorp / Industry Directory",
        "search_category": "decorative_eco_friendly",
        "city": "Bengaluru",
        "state": "Karnataka",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Western India Paint & Colour Company Private Limited",
        "raw_url": "https://www.wipcopaints.com",
        "discovery_source": "Trade Directory / Indiamart",
        "search_category": "industrial_primers_enamels",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Sharp Coating Private Limited",
        "raw_url": "https://www.sharppowdercoatingpowder.com",
        "discovery_source": "Industry Search / Indiamart",
        "search_category": "powder_coatings",
        "city": "Faridabad",
        "state": "Haryana",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Nivera Paints (India) Private Limited",
        "raw_url": "https://www.niverapaints.in",
        "discovery_source": "Industry Search / Indiamart",
        "search_category": "powder_coatings",
        "city": "Faridabad",
        "state": "Haryana",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Sirohi Chemtech Private Limited",
        "raw_url": "https://www.sirohichemtech.com",
        "discovery_source": "Industry Search",
        "search_category": "powder_coatings",
        "city": "Greater Noida",
        "state": "Uttar Pradesh",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Haryana Coating Private Limited",
        "raw_url": "https://www.haryanacoating.com",
        "discovery_source": "Industry Directory",
        "search_category": "powder_coatings_automotive",
        "city": "Gurugram",
        "state": "Haryana",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Maharani Innovative Paints Private Limited",
        "raw_url": "https://www.maharanipaints.com",
        "discovery_source": "Industry Search / ZaubaCorp",
        "search_category": "industrial_powder_coatings",
        "city": "Faridabad",
        "state": "Haryana",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Rini Powder Paints Private Limited",
        "raw_url": "https://www.rinipowder.com",
        "discovery_source": "Industry Directory",
        "search_category": "powder_coatings",
        "city": "Bengaluru",
        "state": "Karnataka",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Satva Coating Private Limited",
        "raw_url": "https://www.satvacoatings.com",
        "discovery_source": "GIDC Directory",
        "search_category": "protective_floor_coatings",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Protective Paints Private Limited",
        "raw_url": "https://www.protectivepaints.com",
        "discovery_source": "GIDC Directory",
        "search_category": "industrial_zinc_primers",
        "city": "Vadodara",
        "state": "Gujarat",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Aakar Paints Private Limited",
        "raw_url": "https://www.aakarpaints.com",
        "discovery_source": "GIDC Directory",
        "search_category": "metal_coatings_pu",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Kirloskar Corrocoat Private Limited",
        "raw_url": "https://www.kirloskarpumps.com",
        "discovery_source": "Corporate Disclosures / JV",
        "search_category": "heavy_duty_corrosion_coatings",
        "city": "Pune",
        "state": "Maharashtra",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Gujarat Colours & Coatings Private Limited",
        "raw_url": "https://www.gujaratcolours.in",
        "discovery_source": "MIDC Directory",
        "search_category": "industrial_pu_coatings",
        "city": "Wada",
        "state": "Maharashtra",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Korrocoat Polymers Private Limited",
        "raw_url": "https://www.korrocoat.com",
        "discovery_source": "MIDC Directory",
        "search_category": "protective_anti_corrosive",
        "city": "Pune",
        "state": "Maharashtra",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Espee Coatings Private Limited",
        "raw_url": "https://www.espeecoatings.com",
        "discovery_source": "MIDC Directory",
        "search_category": "industrial_ceramic_coatings",
        "city": "Amravati",
        "state": "Maharashtra",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Almega Coatings Private Limited",
        "raw_url": "https://www.infomerics.com",
        "discovery_source": "Infomerics Rating Rationale",
        "search_category": "specialty_fusion_coatings",
        "city": "Vadodara",
        "state": "Gujarat",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Sonalac Paints and Coatings Limited",
        "raw_url": "https://www.careratings.com",
        "discovery_source": "CARE Ratings",
        "search_category": "decorative_architectural",
        "city": "Ludhiana",
        "state": "Punjab",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Spectrum Paints Private Limited",
        "raw_url": "https://www.spectrumpaints.com",
        "discovery_source": "Industry Directory",
        "search_category": "textured_architectural_coatings",
        "city": "New Delhi",
        "state": "Delhi",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Gem Paints Private Limited",
        "raw_url": "https://www.gempaints.com",
        "discovery_source": "Astral Disclosures / ZaubaCorp",
        "search_category": "decorative_architectural",
        "city": "Bengaluru",
        "state": "Karnataka",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Snowcem Paints Private Limited",
        "raw_url": "https://www.snowcempaints.com",
        "discovery_source": "Industry Directory / ZaubaCorp",
        "search_category": "exterior_cement_coatings",
        "city": "Mumbai",
        "state": "Maharashtra",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Asian Lacquers & Coatings Private Limited",
        "raw_url": "https://www.asianlacquers.com",
        "discovery_source": "Trade Directory",
        "search_category": "industrial_wood_lacquers",
        "city": "Ludhiana",
        "state": "Punjab",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Ukay Paints Private Limited",
        "raw_url": "https://www.ukaypaints.com",
        "discovery_source": "Trade Directory",
        "search_category": "decorative_industrial",
        "city": "Solan",
        "state": "Himachal Pradesh",
        "initial_classification": "MANUFACTURER"
    },

    {
        "candidate_name": "Asian Paints Limited",
        "raw_url": "https://www.screener.in/company/ASIANPAINT/consolidated/",
        "discovery_source": "Screener.in / NSE",
        "search_category": "decorative_industrial_leader",
        "city": "Mumbai",
        "state": "Maharashtra",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Berger Paints India Limited",
        "raw_url": "https://www.screener.in/company/BERGEPAINT/consolidated/",
        "discovery_source": "Screener.in / NSE",
        "search_category": "decorative_industrial_major",
        "city": "Kolkata",
        "state": "West Bengal",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Kansai Nerolac Paints Limited",
        "raw_url": "https://www.screener.in/company/KANSAINER/consolidated/",
        "discovery_source": "Screener.in / NSE",
        "search_category": "industrial_automotive_decorative",
        "city": "Mumbai",
        "state": "Maharashtra",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Indigo Paints Limited",
        "raw_url": "https://www.screener.in/company/INDIGOPNTS/",
        "discovery_source": "Screener.in / NSE",
        "search_category": "decorative_architectural",
        "city": "Pune",
        "state": "Maharashtra",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Akzo Nobel India Limited",
        "raw_url": "https://www.screener.in/company/500710/",
        "discovery_source": "Screener.in / BSE/NSE",
        "search_category": "decorative_dulux_specialty",
        "city": "Gurugram",
        "state": "Haryana",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "JSW Paints Private Limited",
        "raw_url": "https://www.jswpaints.in",
        "discovery_source": "Corporate Disclosures",
        "search_category": "decorative_industrial_major",
        "city": "Mumbai",
        "state": "Maharashtra",
        "initial_classification": "MANUFACTURER"
    },
    {
        "candidate_name": "Pidilite Industries Limited",
        "raw_url": "https://www.screener.in/company/PIDILITIND/consolidated/",
        "discovery_source": "Screener.in / NSE",
        "search_category": "waterproofing_adhesives_largecap",
        "city": "Mumbai",
        "state": "Maharashtra",
        "initial_classification": "MANUFACTURER"
    },

    {
        "candidate_name": "Heetu Chemicals and Alkalies Limited",
        "raw_url": "https://www.infomerics.com",
        "discovery_source": "Infomerics Rating Rationale",
        "search_category": "raw_material_trading_solvents",
        "city": "Mumbai",
        "state": "Maharashtra",
        "initial_classification": "TRADER_DISTRIBUTOR"
    },
    {
        "candidate_name": "Chemtrade Overseas Private Limited",
        "raw_url": "https://www.infomerics.com",
        "discovery_source": "Infomerics Rating Rationale",
        "search_category": "chemical_importer_trader",
        "city": "New Delhi",
        "state": "Delhi",
        "initial_classification": "TRADER_DISTRIBUTOR"
    }
]

try:
    from scraper_engine.expanded_data import EXPANDED_COMPANIES
    existing_cands = {c["candidate_name"].lower() for c in DISCOVERY_CANDIDATE_CATALOG}
    for _c in EXPANDED_COMPANIES:
        _cname = _c["canonical_name"]
        if _cname.lower() not in existing_cands:
            _raw_url = _c.get("website") or f"https://www.zaubacorp.com/search?q={_cname.replace(' ', '+')}"
            DISCOVERY_CANDIDATE_CATALOG.append({
                "candidate_name": _cname,
                "raw_url": _raw_url,
                "discovery_source": "MCA Master Data / Industry Directory",
                "search_category": _c.get("primary_segment", "coatings"),
                "city": _c.get("city", "India"),
                "state": _c.get("registered_state", "India"),
                "initial_classification": _c.get("manufacturing_status", "MANUFACTURER")
            })
            existing_cands.add(_cname.lower())
except ImportError:
    pass

class DiscoveryScraper:
    def __init__(self, db_path: str = None):
        self.db_path = db_path

    def run_live_screener_discovery(self) -> List[Dict[str, Any]]:
        """Query Screener search API dynamically for paint industry keywords."""
        discovered = []
        queries = [
            "paints", "coatings", "powder coating", "varnish", "resins",
            "industrial paints", "marine paints", "wood coatings", "decorative paints",
            "anti corrosive", "enamels", "wall putty", "waterproofing", "polyurethane coatings", "primer"
        ]
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        
        for q in queries:
            try:
                url = f"https://www.screener.in/api/company/search/?q={q}"
                resp = requests.get(url, headers=headers, timeout=8)
                if resp.status_code == 200:
                    items = resp.json()
                    for it in items:
                        name = it.get("name", "").strip()
                        rel_url = it.get("url", "")
                        if rel_url and name:
                            full_url = f"https://www.screener.in{rel_url}" if rel_url.startswith("/") else rel_url
                            discovered.append({
                                "candidate_name": name,
                                "raw_url": full_url,
                                "discovery_source": f"Screener.in API [q={q}]",
                                "search_category": q,
                                "city": "India",
                                "state": "Pan-India",
                                "initial_classification": "MANUFACTURER" if "resin" not in q else "RESIN_RAW_MATERIAL"
                            })
                time.sleep(0.3)
            except Exception as e:
                logger.warning(f"Screener discovery query '{q}' failed: {e}")

        return discovered

    def discover_all(self) -> List[Dict[str, Any]]:
        """Combine static catalog with dynamic search discoveries and deduplicate."""
        conn = get_connection(self.db_path)
        all_candidates = list(DISCOVERY_CANDIDATE_CATALOG)
        
        dynamic = self.run_live_screener_discovery()
        seen_names = {c["candidate_name"].lower() for c in all_candidates}
        
        for d in dynamic:
            if d["candidate_name"].lower() not in seen_names:
                all_candidates.append(d)
                seen_names.add(d["candidate_name"].lower())

        logger.info(f"Total discovered candidate companies: {len(all_candidates)}")

        for cand in all_candidates:
            conn.execute(
                """
                INSERT INTO discovery_records (
                    candidate_name, raw_url, discovery_source, search_category,
                    city, state, initial_classification, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cand["candidate_name"],
                    cand["raw_url"],
                    cand["discovery_source"],
                    cand["search_category"],
                    cand.get("city", ""),
                    cand.get("state", ""),
                    cand.get("initial_classification", "MANUFACTURER"),
                    "DISCOVERED"
                )
            )

        conn.commit()
        conn.close()
        return all_candidates

if __name__ == "__main__":
    scraper = DiscoveryScraper()
    candidates = scraper.discover_all()
    print(f"Successfully discovered and logged {len(candidates)} candidates.")

