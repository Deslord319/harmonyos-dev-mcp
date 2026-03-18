"""Log parsing, filtering, and effective error extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from ...config import LogSecurityConfig


@dataclass
class LogEntry:
    timestamp: Optional[datetime] = None
    level: Optional[str] = None
    tag: Optional[str] = None
    pid: Optional[int] = None
    tid: Optional[int] = None
    message: str = ""
    raw_line: str = ""


class LogParser:
    PATTERNS = [
        re.compile(
            r"^(?P<date>\d{2}-\d{2})\s+"
            r"(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})\s+"
            r"(?P<pid>\d+)\s+(?P<tid>\d+)\s+"
            r"(?P<level>[DIWEF])\s+"
            r"(?P<tag>[\w\.\-/]+):\s*(?P<message>.*?)$"
        ),
        re.compile(
            r"^(?P<date>\d{4}-\d{2}-\d{2})\s+"
            r"(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})\s+"
            r"(?P<pid>\d+)\s+(?P<tid>\d+)\s+"
            r"(?P<level>[DIWEF])\s+"
            r"(?P<tag>[\w\.\-/]+):\s*(?P<message>.*?)$"
        ),
        re.compile(
            r"^\[(?P<level>[DIWEF])/(?P<tag>[\w\.\-/]+)"
            r"\((?P<pid>\d+):(?P<tid>\d+)\)\]\s*(?P<message>.*?)$"
        ),
        re.compile(
            r"^(?P<level>[DIWEF])/(?P<tag>[\w\.\-/]+)"
            r"\((?P<pid>\d+)\):\s*(?P<message>.*?)$"
        ),
    ]

    LEVEL_NAME_MAP = {
        "D": "D",
        "DEBUG": "D",
        "I": "I",
        "INFO": "I",
        "W": "W",
        "WARN": "W",
        "WARNING": "W",
        "E": "E",
        "ERROR": "E",
        "F": "F",
        "FATAL": "F",
    }
    PRIO_MAP = {"D": 0, "I": 1, "W": 2, "E": 3, "F": 4}

    NOISE_PATTERNS = [
        re.compile(r"/sys/power/last_sr"),
        re.compile(r"XCollie.*last_sr"),
        re.compile(r"Failed to read file:\s*/sys/"),
        re.compile(r"\blogd\b.*\bprune\b", re.IGNORECASE),
        re.compile(r"\bhealthd\b", re.IGNORECASE),
        re.compile(r"\bchatty\b.*\bidentical\b", re.IGNORECASE),
        re.compile(r"ServiceManager:\s*Waiting for service"),
    ]

    ERROR_KEYWORDS = [
        "exception",
        "error",
        "fatal",
        "crash",
        "segmentation fault",
        "sigsegv",
        "anr",
        "abort",
        "assertion",
        "traceback",
        "outofmemory",
        "oom",
        "nullpointer",
        "illegalstate",
        "failed",
        "failure",
        "timeout",
        "refused",
        "denied",
    ]
    SUSPICIOUS_KEYWORDS = [
        "warn",
        "warning",
        "retry",
        "deprecated",
        "slow",
        "blocked",
        "leak",
        "overflow",
        "underflow",
        "drop",
        "unavailable",
        "unexpected",
        "invalid",
        "stuck",
        "freeze",
        "hang",
    ]

    @classmethod
    def normalize_level(cls, level: Optional[str]) -> Optional[str]:
        if not level:
            return None
        return cls.LEVEL_NAME_MAP.get(level.strip().upper())

    @classmethod
    def normalize_domain(cls, domain: str) -> str:
        if not domain:
            return ""
        d = domain.upper().replace("0X", "").replace("X", "")
        if len(d) == 4:
            return f"C{d}"
        if len(d) == 5 and d.startswith("C"):
            return d
        if len(d) == 6:
            return d
        return f"C{d.zfill(4)}"

    @classmethod
    def parse_line(cls, line: str, year: Optional[int] = None) -> LogEntry:
        if year is None:
            year = datetime.now().year
        raw = line.rstrip()
        entry = LogEntry(raw_line=raw)

        for pattern in cls.PATTERNS:
            match = pattern.match(raw)
            if not match:
                continue
            g = match.groupdict()

            if "date" in g and "time" in g:
                try:
                    date_str = g["date"]
                    if len(date_str) == 5:
                        date_str = f"{year}-{date_str}"
                    ts = datetime.strptime(f"{date_str} {g['time']}", "%Y-%m-%d %H:%M:%S.%f")
                    if ts > datetime.now() + timedelta(days=1):
                        ts = ts.replace(year=ts.year - 1)
                    entry.timestamp = ts
                except ValueError:
                    pass

            entry.level = g.get("level")
            entry.tag = g.get("tag")
            if g.get("pid"):
                try:
                    entry.pid = int(g["pid"])
                except ValueError:
                    pass
            if g.get("tid"):
                try:
                    entry.tid = int(g["tid"])
                except ValueError:
                    pass
            entry.message = (g.get("message") or "").strip()
            break

        if not entry.level:
            entry.message = raw
        return entry

    @classmethod
    def parse_logs(cls, lines: List[str], year: Optional[int] = None) -> List[LogEntry]:
        return [cls.parse_line(line, year) for line in lines if line.strip()]

    @classmethod
    def _is_noise(cls, entry: LogEntry) -> bool:
        text = entry.message or entry.raw_line
        return any(p.search(text) for p in cls.NOISE_PATTERNS)

    @classmethod
    def filter_entries(
        cls,
        entries: List[LogEntry],
        level: Optional[str] = None,
        tag: Optional[str] = None,
        tag_search: Optional[str] = None,
        keyword: Optional[str] = None,
        domain: Optional[str] = None,
        time_range: Optional[Dict] = None,
        pid: Optional[int] = None,
        seconds: Optional[int] = None,
        package_name: Optional[str] = None,
    ) -> List[LogEntry]:
        min_p = None
        if level:
            n = cls.normalize_level(level)
            min_p = cls.PRIO_MAP.get(n, 0) if n else 0

        tag_lower = tag.lower() if tag else None
        tag_search_lower = tag_search.lower() if tag_search else None
        kw_lower = keyword.lower() if keyword else None
        pkg_lower = package_name.lower() if package_name else None
        domain_norm = cls.normalize_domain(domain) if domain else None

        start_dt = time_range.get("start") if time_range else None
        end_dt = time_range.get("end") if time_range else None
        cutoff = datetime.now() - timedelta(seconds=seconds) if seconds else None

        result = []
        for entry in entries:
            if min_p is not None and (not entry.level or cls.PRIO_MAP.get(entry.level.upper(), 0) < min_p):
                continue
            if tag_lower and (not entry.tag or tag_lower not in entry.tag.lower()):
                continue
            if tag_search_lower and tag_search_lower not in entry.raw_line.lower():
                continue
            if kw_lower and kw_lower not in entry.raw_line.lower():
                continue
            if domain_norm and domain_norm not in entry.raw_line.upper():
                continue
            if pid and entry.pid != pid:
                continue
            if start_dt and (not entry.timestamp or entry.timestamp < start_dt):
                continue
            if end_dt and (not entry.timestamp or entry.timestamp > end_dt):
                continue
            if cutoff and (not entry.timestamp or entry.timestamp < cutoff):
                continue
            if pkg_lower and pkg_lower not in entry.raw_line.lower():
                continue
            if LogSecurityConfig.ENABLE_NOISE_FILTER and cls._is_noise(entry):
                continue
            result.append(entry)
        return result

    @classmethod
    def extract_effective_errors(cls, entries: List[LogEntry], limit: int = 200) -> List[Dict[str, object]]:
        findings: List[Dict[str, object]] = []
        seen = set()
        max_items = max(1, limit)

        for entry in entries:
            raw = entry.raw_line or ""
            msg = entry.message or raw
            msg_lower = msg.lower()
            level = (entry.level or "").upper()

            is_error_level = level in ("E", "F")
            error_hits = [k for k in cls.ERROR_KEYWORDS if k in msg_lower]
            suspicious_hits = [k for k in cls.SUSPICIOUS_KEYWORDS if k in msg_lower]
            if not is_error_level and not error_hits and not suspicious_hits:
                continue

            finding_type = "error" if (is_error_level or error_hits) else "suspicious"
            severity = 100 if level == "F" else 90 if level == "E" else 70 if error_hits else 50
            dedup_key = (entry.tag or "", msg.strip()[:160], finding_type)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            findings.append(
                {
                    "type": finding_type,
                    "severity": severity,
                    "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                    "level": level or None,
                    "tag": entry.tag,
                    "pid": entry.pid,
                    "message": msg.strip(),
                    "raw_line": raw,
                    "error_keywords": error_hits,
                    "suspicious_keywords": suspicious_hits,
                }
            )

        findings.sort(key=lambda x: ((x.get("severity") or 0), (x.get("timestamp") or "")), reverse=True)
        return findings[:max_items]
