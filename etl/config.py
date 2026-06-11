BASE_URL = "https://otel-hackathon-data-site.vercel.app"
REQUEST_DELAY_MS = 400
DETAIL_MAX_RETRIES = 3
NAVIGATION_TIMEOUT_MS = 30_000
ELEMENT_TIMEOUT_MS = 15_000
MAX_LIST_PAGES = 20

OUTPUT_RESERVATIONS = "data/raw_reservations.json"
OUTPUT_LOOKUPS = "data/raw_lookups.json"

# From docs/GROUND_TRUTH.md (anchor date 2026-06-10)
EXPECTED_ANCHOR_DATE = "2026-06-10"
EXPECTED = {
    "total_reservations": 250,
    "total_stay_rows": 549,
    "room_type_lookup": 3,
    "market_code_lookup": 10,
    "channel_code_lookup": 4,
}

LOOKUP_SORT_KEYS = {
    "room_type_lookup": "space_type",
    "market_code_lookup": "market_code",
    "channel_code_lookup": "channel_code",
}
