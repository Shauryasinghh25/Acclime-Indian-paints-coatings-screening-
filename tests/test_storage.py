import pytest
import sqlite3
import tempfile
from pathlib import Path
from scraper_engine.db import init_db, get_connection
from scraper_engine.storage import StorageManager
from scraper_engine.extractor import Extractor

FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture
def test_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    init_db(db_path)
    yield db_path
    import gc
    gc.collect()
    try:
        Path(db_path).unlink(missing_ok=True)
    except PermissionError:
        pass

def test_deduplication_by_cin(test_db):
    storage = StorageManager()
    extractor = Extractor()
    html_content = (FIXTURES_DIR / "sample_sirca.html").read_bytes()

    import scraper_engine.storage
    import scraper_engine.db
    orig_get_conn = scraper_engine.db.get_connection
    scraper_engine.storage.get_connection = lambda: sqlite3.connect(test_db)
    scraper_engine.db.get_connection = lambda: sqlite3.connect(test_db)

    try:
        source_id = storage.record_source("https://www.sircapaints.com", "Sirca Homepage", "WEBSITE_HTML")
        extracted = extractor.extract_from_html(html_content, "https://www.sircapaints.com")

        cid_1 = storage.store_extracted_data(extracted, source_id)
        assert cid_1 is not None

        source_id_2 = storage.record_source("https://www.sircapaints.com/about", "Sirca About", "WEBSITE_HTML")
        cid_2 = storage.store_extracted_data(extracted, source_id_2)

        assert cid_1 == cid_2

        conn = sqlite3.connect(test_db)
        count = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
        assert count == 1
        conn.close()
    finally:
        scraper_engine.storage.get_connection = orig_get_conn
        scraper_engine.db.get_connection = orig_get_conn
