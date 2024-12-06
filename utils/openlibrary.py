from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests_cache import CachedSession
import datetime

# Configure session with retries and caching
session = CachedSession(
    "openlibrary_cache",
    expire_after=datetime.timedelta(hours=1),
    backend="sqlite",
)

retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)

adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("http://", adapter)
session.mount("https://", adapter)
session.headers.update({"User-Agent": "Library App (chrisgo@bu.edu)"})
