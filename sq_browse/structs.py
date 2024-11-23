from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class BrowserResponse(object):
    url: str
    requested_url: str
    status_code: int
    reason: str
    response_headers: Dict[str, str]
    content: str
    timestamp_start: datetime
    elapsed: timedelta
