"""Log parsing, filtering, and query item extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Sequence

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
    SUCCESS_PATTERNS = [
        re.compile(r"\berror\s*code\s*[:=]\s*0\b", re.IGNORECASE),
        re.compile(r"\berrorcode\s+is\s*=\s*0\b", re.IGNORECASE),
        re.compile(r"\berrcode\s*[:=]\s*0\b", re.IGNORECASE),
        re.compile(r"\brescode\s+is\s*0\b", re.IGNORECASE),
        re.compile(r"\bsuccess\s*=\s*true\b", re.IGNORECASE),
        re.compile(r"\bresult\s*:\s*ok\b", re.IGNORECASE),
        re.compile(r"\bcompleted successfully\b", re.IGNORECASE),
    ]
    DEFAULT_MARKER_KEYWORDS = (
        "saveResult",
        "resCode is 0",
        "success",
        "completed",
        "saved",
        "export",
        "picker",
        "selecturi",
    )
    DEFAULT_RELATED_KEYWORDS = (
        "picker",
        "documentpicker",
        "document picker",
        "selecturi",
        "file://docs/storage",
    )
    WEAK_MARKER_KEYWORDS = {
        "success",
        "completed",
        "saved",
        "save",
        "export",
        ".csv",
        ".txt",
        ".log",
    }

    @classmethod
    def normalize_level(cls, level: Optional[str]) -> Optional[str]:
        if not level:
            return None
        return cls.LEVEL_NAME_MAP.get(level.strip().upper())

    @classmethod
    def normalize_domain(cls, domain: str) -> str:
        if not domain:
            return ""
        normalized = domain.upper().replace("0X", "").replace("X", "")
        if len(normalized) == 4:
            return f"C{normalized}"
        if len(normalized) == 5 and normalized.startswith("C"):
            return normalized
        if len(normalized) == 6:
            return normalized
        return f"C{normalized.zfill(4)}"

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
            groups = match.groupdict()

            if "date" in groups and "time" in groups:
                try:
                    date_str = groups["date"]
                    if len(date_str) == 5:
                        date_str = f"{year}-{date_str}"
                    ts = datetime.strptime(f"{date_str} {groups['time']}", "%Y-%m-%d %H:%M:%S.%f")
                    if ts > datetime.now() + timedelta(days=1):
                        ts = ts.replace(year=ts.year - 1)
                    entry.timestamp = ts
                except ValueError:
                    pass

            entry.level = groups.get("level")
            entry.tag = groups.get("tag")
            if groups.get("pid"):
                try:
                    entry.pid = int(groups["pid"])
                except ValueError:
                    pass
            if groups.get("tid"):
                try:
                    entry.tid = int(groups["tid"])
                except ValueError:
                    pass
            entry.message = (groups.get("message") or "").strip()
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
        return any(pattern.search(text) for pattern in cls.NOISE_PATTERNS)

    @classmethod
    def _text_parts(cls, entry: LogEntry) -> tuple[str, str, str]:
        raw_lower = entry.raw_line.lower()
        msg_lower = (entry.message or entry.raw_line).lower()
        tag_lower = (entry.tag or "").lower()
        return raw_lower, msg_lower, tag_lower

    @classmethod
    def _package_matches(
        cls,
        entry: LogEntry,
        package_name: Optional[str],
        related_pids: Optional[Sequence[int]] = None,
        related_keywords: Optional[Sequence[str]] = None,
        allow_related_without_package: bool = False,
    ) -> bool:
        if not package_name and not related_pids and not related_keywords:
            return True

        raw_lower, msg_lower, tag_lower = cls._text_parts(entry)
        package_lower = package_name.lower() if package_name else None

        if package_lower and (
            package_lower in raw_lower or package_lower in msg_lower or package_lower in tag_lower
        ):
            return True

        if related_pids and entry.pid in set(related_pids):
            return True

        if allow_related_without_package and related_keywords:
            for keyword in related_keywords:
                kw = keyword.lower()
                if kw and (kw in raw_lower or kw in msg_lower or kw in tag_lower):
                    return True

        return package_name is None

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
        related_pids: Optional[Sequence[int]] = None,
        related_keywords: Optional[Sequence[str]] = None,
        allow_related_without_package: bool = False,
    ) -> List[LogEntry]:
        min_priority = None
        if level:
            normalized = cls.normalize_level(level)
            min_priority = cls.PRIO_MAP.get(normalized, 0) if normalized else 0

        tag_lower = tag.lower() if tag else None
        tag_search_lower = tag_search.lower() if tag_search else None
        keyword_lower = keyword.lower() if keyword else None
        domain_norm = cls.normalize_domain(domain) if domain else None
        related_pid_set = set(related_pids or [])

        start_dt = time_range.get("start") if time_range else None
        end_dt = time_range.get("end") if time_range else None
        cutoff = datetime.now() - timedelta(seconds=seconds) if seconds else None

        result = []
        for entry in entries:
            if min_priority is not None and (not entry.level or cls.PRIO_MAP.get(entry.level.upper(), 0) < min_priority):
                continue
            if tag_lower and (not entry.tag or tag_lower not in entry.tag.lower()):
                continue
            if tag_search_lower and tag_search_lower not in entry.raw_line.lower():
                continue
            if keyword_lower and keyword_lower not in entry.raw_line.lower():
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
            if package_name or related_pid_set or related_keywords:
                if not cls._package_matches(
                    entry,
                    package_name=package_name,
                    related_pids=related_pid_set,
                    related_keywords=related_keywords,
                    allow_related_without_package=allow_related_without_package,
                ):
                    continue
            if LogSecurityConfig.ENABLE_NOISE_FILTER and cls._is_noise(entry):
                continue
            result.append(entry)
        return result

    @classmethod
    def is_success_message(cls, message: str) -> bool:
        return any(pattern.search(message) for pattern in cls.SUCCESS_PATTERNS)

    @classmethod
    def _build_item(
        cls,
        *,
        entries: Sequence[LogEntry],
        index: int,
        item_type: str,
        matched_keywords: Iterable[str],
        severity: Optional[int] = None,
        context_lines: int = 0,
    ) -> Dict[str, object]:
        entry = entries[index]
        before = []
        after = []
        if context_lines > 0:
            start = max(0, index - context_lines)
            end = min(len(entries), index + context_lines + 1)
            before = [item.raw_line for item in entries[start:index]]
            after = [item.raw_line for item in entries[index + 1 : end]]

        result = {
            "type": item_type,
            "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
            "level": entry.level or None,
            "tag": entry.tag,
            "pid": entry.pid,
            "message": (entry.message or entry.raw_line).strip(),
            "raw_line": entry.raw_line,
            "context_before": before,
            "context_after": after,
            "matched_keywords": sorted(set(keyword for keyword in matched_keywords if keyword)),
        }
        if severity is not None:
            result["severity"] = severity
        return result

    @classmethod
    def _classify_marker_keywords(cls, matched_keywords: Sequence[str]) -> Dict[str, List[str]]:
        strong = []
        weak = []
        for keyword in matched_keywords:
            normalized = keyword.strip()
            if not normalized:
                continue
            lowered = normalized.lower()
            if lowered in cls.WEAK_MARKER_KEYWORDS:
                weak.append(normalized)
                continue
            if lowered.startswith("."):
                weak.append(normalized)
                continue
            strong.append(normalized)
        return {"strong": strong, "weak": weak}

    @classmethod
    def _extract_group_key(cls, entry: LogEntry, matched_keywords: Sequence[str]) -> str:
        strong_keywords = cls._classify_marker_keywords(matched_keywords)["strong"]
        source_parts = []
        if entry.tag:
            source_parts.append(entry.tag.lower())
        if entry.pid is not None:
            source_parts.append(f"pid:{entry.pid}")
        source_key = "|".join(source_parts)

        if strong_keywords and source_key:
            return f"{source_key}|{'|'.join(sorted(keyword.lower() for keyword in strong_keywords))}"
        if strong_keywords:
            return "|".join(sorted(keyword.lower() for keyword in strong_keywords))
        if source_key:
            return source_key
        return ""

    @classmethod
    def _time_score(cls, entry: LogEntry, reference_time: Optional[datetime]) -> int:
        if not entry.timestamp or not reference_time:
            return 0
        distance = abs((reference_time - entry.timestamp).total_seconds())
        if distance <= 2:
            return 15
        if distance <= 5:
            return 8
        if distance <= 10:
            return 3
        return 0

    @classmethod
    def _marker_score(
        cls,
        *,
        entry: LogEntry,
        package_name: Optional[str],
        related_pids: Optional[Sequence[int]],
        keyword_types: Dict[str, List[str]],
        reference_time: Optional[datetime],
    ) -> int:
        raw_lower, msg_lower, tag_lower = cls._text_parts(entry)
        score = 0

        score += len(keyword_types["strong"]) * 40
        score += len(keyword_types["weak"]) * 8

        if package_name:
            package_lower = package_name.lower()
            if package_lower in raw_lower or package_lower in msg_lower or package_lower in tag_lower:
                score += 25

        if related_pids and entry.pid in set(related_pids):
            score += 20

        score += cls._time_score(entry, reference_time)
        return score

    @classmethod
    def _should_keep_marker(
        cls,
        *,
        score: int,
        keyword_types: Dict[str, List[str]],
        package_name: Optional[str],
        entry: LogEntry,
    ) -> bool:
        if keyword_types["strong"]:
            return True
        if score >= 50:
            return True
        if package_name and entry.tag and package_name.lower() in entry.tag.lower() and score >= 40:
            return True
        return False

    @classmethod
    def _marker_reference_time(cls, entries: Sequence[LogEntry]) -> Optional[datetime]:
        timestamps = [entry.timestamp for entry in entries if entry.timestamp is not None]
        return max(timestamps) if timestamps else None

    @classmethod
    def _group_marker_items(cls, items: List[Dict[str, object]]) -> List[Dict[str, object]]:
        grouped: Dict[str, List[Dict[str, object]]] = {}
        passthrough: List[Dict[str, object]] = []

        for item in items:
            group_key = str(item.get("group_key") or "")
            if not group_key:
                passthrough.append(item)
                continue
            grouped.setdefault(group_key, []).append(item)

        result = list(passthrough)
        for group_key, group_items in grouped.items():
            if len(group_items) == 1:
                result.extend(group_items)
                continue
            timestamps = [datetime.fromisoformat(item["timestamp"]) for item in group_items if item.get("timestamp")]
            if timestamps:
                if (max(timestamps) - min(timestamps)).total_seconds() > 5:
                    result.extend(group_items)
                    continue
            ordered = sorted(group_items, key=lambda item: (item.get("score") or 0, item.get("timestamp") or ""), reverse=True)
            primary = dict(ordered[0])
            primary["group_key"] = group_key
            primary["group_score"] = max(int(item.get("score") or 0) for item in ordered) + min(len(ordered) * 5, 15)
            primary["related_items"] = [
                {
                    "timestamp": item.get("timestamp"),
                    "tag": item.get("tag"),
                    "message": item.get("message"),
                    "score": item.get("score"),
                    "matched_keywords": item.get("matched_keywords"),
                }
                for item in ordered[1:]
            ]
            primary["score"] = primary["group_score"]
            result.append(primary)

        result.sort(key=lambda item: ((item.get("score") or 0), (item.get("timestamp") or "")), reverse=True)
        return result

    @classmethod
    def extract_error_items(
        cls,
        entries: List[LogEntry],
        *,
        limit: int = 200,
        context_lines: int = 0,
    ) -> List[Dict[str, object]]:
        findings: List[Dict[str, object]] = []
        seen = set()

        for index, entry in enumerate(entries):
            raw = entry.raw_line or ""
            msg = entry.message or raw
            msg_lower = msg.lower()
            level = (entry.level or "").upper()

            if cls.is_success_message(msg):
                continue

            is_error_level = level in ("E", "F")
            error_hits = [keyword for keyword in cls.ERROR_KEYWORDS if keyword in msg_lower]
            suspicious_hits = [keyword for keyword in cls.SUSPICIOUS_KEYWORDS if keyword in msg_lower]
            if not is_error_level and not error_hits and not suspicious_hits:
                continue

            item_type = "error" if (is_error_level or error_hits) else "suspicious"
            severity = 100 if level == "F" else 90 if level == "E" else 70 if error_hits else 50
            dedup_key = (entry.tag or "", msg.strip()[:160], item_type)
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            item = cls._build_item(
                entries=entries,
                index=index,
                item_type=item_type,
                matched_keywords=[*error_hits, *suspicious_hits],
                severity=severity,
                context_lines=context_lines,
            )
            item["error_keywords"] = error_hits
            item["suspicious_keywords"] = suspicious_hits
            findings.append(item)

        findings.sort(key=lambda item: ((item.get("severity") or 0), (item.get("timestamp") or "")), reverse=True)
        return findings[: max(1, limit)]

    @classmethod
    def extract_marker_items(
        cls,
        entries: List[LogEntry],
        *,
        limit: int = 200,
        marker_keywords: Optional[Sequence[str]] = None,
        context_lines: int = 0,
        package_name: Optional[str] = None,
        related_pids: Optional[Sequence[int]] = None,
    ) -> Dict[str, object]:
        keywords = [keyword for keyword in (marker_keywords or cls.DEFAULT_MARKER_KEYWORDS) if keyword]
        items: List[Dict[str, object]] = []
        seen = set()
        reference_time = cls._marker_reference_time(entries)

        for index, entry in enumerate(entries):
            raw_lower, msg_lower, tag_lower = cls._text_parts(entry)
            matched = [
                keyword
                for keyword in keywords
                if keyword.lower() in raw_lower or keyword.lower() in msg_lower or keyword.lower() in tag_lower
            ]
            if not matched:
                continue

            keyword_types = cls._classify_marker_keywords(matched)
            score = cls._marker_score(
                entry=entry,
                package_name=package_name,
                related_pids=related_pids,
                keyword_types=keyword_types,
                reference_time=reference_time,
            )
            if not cls._should_keep_marker(
                score=score,
                keyword_types=keyword_types,
                package_name=package_name,
                entry=entry,
            ):
                continue

            item_type = "marker_success" if cls.is_success_message(entry.message or entry.raw_line) else "marker"
            dedup_key = (entry.tag or "", (entry.message or entry.raw_line).strip()[:200], tuple(sorted(matched)))
            if dedup_key in seen:
                continue
            seen.add(dedup_key)
            items.append(
                cls._build_item(
                    entries=entries,
                    index=index,
                    item_type=item_type,
                    matched_keywords=matched,
                    context_lines=context_lines,
                )
            )
            items[-1]["score"] = score
            items[-1]["match_strength"] = "strong" if keyword_types["strong"] else "weak"
            items[-1]["matched_keyword_types"] = keyword_types
            items[-1]["group_key"] = cls._extract_group_key(entry, matched)

        grouped = cls._group_marker_items(items)
        limited = grouped[: max(1, limit)]
        return {
            "items": limited,
            "match_count": len(items),
            "group_count": len(limited),
        }
