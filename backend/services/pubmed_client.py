import time
import logging
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────
NCBI_BASE        = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
SEARCH_URL       = f"{NCBI_BASE}/esearch.fcgi"
FETCH_URL        = f"{NCBI_BASE}/efetch.fcgi"
ABSTRACTS_DIR    = Path(__file__).parent.parent / "data" / "abstracts"
MAX_RESULTS      = 5          
REQUEST_DELAY    = 0.4       
REQUEST_TIMEOUT  = 8         
TOOL_NAME        = "RareMatch" 
TOOL_EMAIL       = "rarematch@hackathon.dev"


# ── Main Client Class ──────────────────────────────────────────
class PubMedClient:

    def __init__(self):
        ABSTRACTS_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("PubMedClient initialized")

    # ── Public Methods ─────────────────────────────────────────

    def fetch_abstracts(self, disease_name: str) -> tuple[str, str]:
        """
        Main entry point.
        Returns: (abstract_text, source)
          source is 'pubmed_live' | 'cache' | 'fallback'

        Always tries live first, falls back to cache, then empty string.
        """
        # Step 1: Try live PubMed
        try:
            pmids = self._search_pmids(disease_name)
            if pmids:
                abstracts = self._fetch_abstracts_by_pmids(pmids)
                if abstracts:
                    self._cache_abstracts(disease_name, abstracts)
                    logger.info(
                        f"Fetched {len(pmids)} abstracts live for '{disease_name}'"
                    )
                    return abstracts, "pubmed_live"
        except Exception as e:
            logger.warning(f"PubMed live fetch failed for '{disease_name}': {e}")

        # Step 2: Fall back to cached file
        cached = self._load_cache(disease_name)
        if cached:
            logger.info(f"Using cached abstracts for '{disease_name}'")
            return cached, "cache"

        # Step 3: Return empty — inference engine handles this gracefully
        logger.error(f"No abstracts available for '{disease_name}' — live and cache both failed")
        return "", "fallback"

    def get_abstract_by_pmid(self, pmid: str) -> Optional[str]:
        """
        Fetch a single abstract by PMID.
        Used for evidence verification in the UI deep-dive panel.
        """
        try:
            result = self._fetch_abstracts_by_pmids([pmid.replace("PMID:", "").strip()])
            return result if result else None
        except Exception as e:
            logger.warning(f"Failed to fetch PMID {pmid}: {e}")
            return None

    # ── Private Methods ────────────────────────────────────────

    def _search_pmids(self, disease_name: str) -> list[str]:
        """
        Search PubMed for disease name.
        Returns list of top PMIDs (max MAX_RESULTS).
        """
        # Build search query — add [Title/Abstract] to improve relevance
        query = f"{disease_name}[Title/Abstract] AND (mechanism OR pathway OR gene OR mutation)"

        params = urllib.parse.urlencode({
            "db":       "pubmed",
            "term":     query,
            "retmax":   MAX_RESULTS,
            "retmode":  "json",
            "sort":     "relevance",
            "tool":     TOOL_NAME,
            "email":    TOOL_EMAIL,
        })

        url      = f"{SEARCH_URL}?{params}"
        response = self._make_request(url)

        if not response:
            return []

        import json
        try:
            data  = json.loads(response)
            pmids = data.get("esearchresult", {}).get("idlist", [])
            logger.info(f"PubMed search for '{disease_name}' returned PMIDs: {pmids}")
            return pmids
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse PubMed search results: {e}")
            return []

    def _fetch_abstracts_by_pmids(self, pmids: list[str]) -> str:
        """
        Fetch full abstract text for a list of PMIDs.
        Returns concatenated abstract text.
        """
        if not pmids:
            return ""

        time.sleep(REQUEST_DELAY)  # Respect NCBI rate limit

        params = urllib.parse.urlencode({
            "db":       "pubmed",
            "id":       ",".join(pmids),
            "rettype":  "abstract",
            "retmode":  "xml",
            "tool":     TOOL_NAME,
            "email":    TOOL_EMAIL,
        })

        url      = f"{FETCH_URL}?{params}"
        response = self._make_request(url)

        if not response:
            return ""

        return self._parse_abstract_xml(response, pmids)

    def _parse_abstract_xml(self, xml_text: str, pmids: list[str]) -> str:
        """
        Parse PubMed XML response and extract abstract text.
        Returns clean concatenated text with PMID labels.
        """
        try:
            root    = ET.fromstring(xml_text)
            entries = []

            for i, article in enumerate(root.findall(".//PubmedArticle")):

                # Extract PMID
                pmid_el = article.find(".//PMID")
                pmid    = pmid_el.text if pmid_el is not None else pmids[i] if i < len(pmids) else "Unknown"

                # Extract title
                title_el = article.find(".//ArticleTitle")
                title    = title_el.text if title_el is not None else "No title"
                # Remove XML markup artifacts
                title = "".join(title_el.itertext()) if title_el is not None else "No title"

                # Extract abstract — handle structured abstracts with multiple sections
                abstract_texts = []
                abstract_el    = article.find(".//Abstract")
                if abstract_el is not None:
                    for text_el in abstract_el.findall(".//AbstractText"):
                        label = text_el.get("Label", "")
                        text  = "".join(text_el.itertext()).strip()
                        if text:
                            if label:
                                abstract_texts.append(f"{label}: {text}")
                            else:
                                abstract_texts.append(text)

                abstract = " ".join(abstract_texts) if abstract_texts else "Abstract not available."

                entries.append(
                    f"ABSTRACT {i+1} — PMID: {pmid}\n"
                    f"Title: {title}\n"
                    f"{abstract}"
                )

            result = "\n\n".join(entries)
            logger.info(f"Parsed {len(entries)} abstracts from PubMed XML")
            return result

        except ET.ParseError as e:
            logger.error(f"XML parse error from PubMed: {e}")
            return ""

    def _make_request(self, url: str) -> Optional[str]:
        """
        Single HTTP request handler.
        Returns response text or None on failure.
        All network calls go through here — single point for error handling.
        """
        try:
            req      = urllib.request.Request(
                url,
                headers={"User-Agent": f"{TOOL_NAME}/1.0 ({TOOL_EMAIL})"}
            )
            response = urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT)
            return response.read().decode("utf-8")
        except urllib.error.URLError as e:
            logger.warning(f"Network error fetching {url[:80]}...: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error fetching URL: {e}")
            return None

    def _cache_abstracts(self, disease_name: str, text: str) -> None:
        """
        Save fetched abstracts to local cache file.
        Filename: lowercase disease name with spaces as underscores.
        """
        filename = disease_name.lower().replace(" ", "_") + ".txt"
        filepath = ABSTRACTS_DIR / filename
        try:
            filepath.write_text(text, encoding="utf-8")
            logger.info(f"Cached abstracts to {filename}")
        except Exception as e:
            logger.warning(f"Failed to cache abstracts for '{disease_name}': {e}")

    def _load_cache(self, disease_name: str) -> Optional[str]:
        """
        Load cached abstracts from local .txt file.
        Returns None if no cache exists.
        """
        filename = disease_name.lower().replace(" ", "_") + ".txt"
        filepath = ABSTRACTS_DIR / filename
        if filepath.exists():
            try:
                return filepath.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to read cache file {filename}: {e}")
        return None