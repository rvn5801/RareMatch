import json
import time
import logging
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional

logger = logging.getLogger(__name__)

OPENFDA_BASE    = "https://api.fda.gov/drug/label.json"
REQUEST_TIMEOUT = 6
REQUEST_DELAY   = 0.3


class OpenFDAClient:

    def __init__(self):
        self._cache: dict = {}   # In-memory cache: query → result
        logger.info("OpenFDAClient initialized")

    def fetch_label(self, drug_query: str) -> Optional[dict]:
        """
        Fetch FDA drug label for a given drug name.
        Returns dict with key safety fields or None if not found.

        Cached in memory — duplicate calls within a session are free.
        """
        if drug_query in self._cache:
            return self._cache[drug_query]

        try:
            time.sleep(REQUEST_DELAY)
            encoded = urllib.parse.quote(f'"{drug_query}"')
            url     = f"{OPENFDA_BASE}?search=openfda.generic_name:{encoded}&limit=1"
            req     = urllib.request.Request(
                url,
                headers={"User-Agent": "RareMatch/1.0 (rarematch@hackathon.dev)"}
            )
            response = urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT)
            raw      = response.read().decode("utf-8")
            data     = json.loads(raw)

            results = data.get("results", [])
            if not results:
                logger.info(f"OpenFDA: no label found for '{drug_query}'")
                self._cache[drug_query] = None
                return None

            label  = results[0]
            parsed = {
                "boxed_warning":     self._extract(label, "boxed_warning"),
                "warnings":          self._extract(label, "warnings"),
                "pediatric_use":     self._extract(label, "pediatric_use"),
                "contraindications": self._extract(label, "contraindications"),
                "adverse_reactions": self._extract(label, "adverse_reactions"),
            }

            self._cache[drug_query] = parsed
            logger.info(f"OpenFDA label fetched for '{drug_query}'")
            return parsed

        except urllib.error.HTTPError as e:
            if e.code == 404:
                logger.info(f"OpenFDA 404 — no label for '{drug_query}'")
            else:
                logger.warning(f"OpenFDA HTTP {e.code} for '{drug_query}'")
            self._cache[drug_query] = None
            return None

        except Exception as e:
            logger.warning(f"OpenFDA fetch failed for '{drug_query}': {e}")
            self._cache[drug_query] = None
            return None

    def _extract(self, label: dict, field: str) -> Optional[str]:
        """Extract a text field from FDA label — handles list or string."""
        value = label.get(field)
        if isinstance(value, list) and value:
            return value[0][:600]
        if isinstance(value, str):
            return value[:600]
        return None