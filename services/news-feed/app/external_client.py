"""뉴스·공시·거시 소스 클라이언트 (부패방지 계층). ADR 0008.

- 뉴스: RSS(무료)·Naver 뉴스검색(무료 키) → 내부 표준 `{title, body, source_url, license, published_at}`
- 공시: DART(무료 키) → 위와 동일
- 거시: ECOS(한국은행)·FRED(미 연준, 무료 키) → `{name, value, unit, as_of, source, source_url}`
외부 스키마를 내부 표준으로 변환·격리한다. 가드레일: 출처 URL·라이선스 메타 필수 동반.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import httpx

_TAG_RE = re.compile(r"<[^>]+>")


def _clean_html(text: str) -> str:
    """네이버 검색 결과의 HTML 태그·엔티티 제거."""
    text = _TAG_RE.sub("", text)
    for a, b in (("&quot;", '"'), ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&nbsp;", " ")):
        text = text.replace(a, b)
    return text.strip()


def _entry_ts(entry: Any) -> str:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime(
            parsed[0], parsed[1], parsed[2], parsed[3], parsed[4], parsed[5], tzinfo=timezone.utc
        ).isoformat()
    return datetime.now(timezone.utc).isoformat()


class RssClient:
    """공개 뉴스 RSS 수집(키 없음)."""

    def __init__(self, feed_urls: list[str]) -> None:
        self._feed_urls = feed_urls

    def fetch(self, limit_per_feed: int = 10) -> list[dict[str, Any]]:
        docs: list[dict[str, Any]] = []
        for url in self._feed_urls:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:limit_per_feed]:
                link = str(entry.get("link", ""))
                if not link:
                    continue  # 가드레일: 출처 없는 항목 제외
                docs.append({
                    "title": str(entry.get("title", "")),
                    "body": str(entry.get("summary", entry.get("description", ""))),
                    "source_url": link,
                    "license": "RSS",
                    "published_at": _entry_ts(entry),
                })
        return docs


class NaverNewsClient:
    """네이버 뉴스검색(openapi.naver.com, 무료 키) — 종목명으로 타깃 검색. ADR 0008."""

    def __init__(self, client_id: str = "", client_secret: str = "") -> None:
        self._id = client_id
        self._secret = client_secret

    def search(self, queries: list[str], display: int = 10) -> list[dict[str, Any]]:
        """종목명 리스트로 각각 최신순 검색 → 내부 표준 docs. 키 없으면 스킵."""
        if not (self._id and self._secret):
            return []
        headers = {"X-Naver-Client-Id": self._id, "X-Naver-Client-Secret": self._secret}
        docs: list[dict[str, Any]] = []
        for query in queries:
            resp = httpx.get(
                "https://openapi.naver.com/v1/search/news.json",
                params={"query": query, "display": display, "sort": "date"},
                headers=headers,
                timeout=30,
            )
            if resp.status_code != 200:
                continue
            for item in resp.json().get("items", []):
                link = str(item.get("originallink") or item.get("link") or "")
                if not link:
                    continue  # 가드레일: 출처 없는 항목 제외
                docs.append({
                    "title": _clean_html(str(item.get("title", ""))),
                    "body": _clean_html(str(item.get("description", ""))),
                    "source_url": link,
                    "license": "NAVER",
                    "published_at": _naver_ts(str(item.get("pubDate", ""))),
                })
        return docs


def _naver_ts(pub_date: str) -> str:
    """네이버 pubDate(RFC822) → ISO8601 UTC. 실패 시 현재."""
    try:
        return parsedate_to_datetime(pub_date).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return datetime.now(timezone.utc).isoformat()


def _dart_ts(yyyymmdd: str) -> str:
    if len(yyyymmdd) == 8 and yyyymmdd.isdigit():
        return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}T00:00:00+00:00"
    return datetime.now(timezone.utc).isoformat()


class DartClient:
    """DART 공시(opendart.fss.or.kr) — 무료 API 키 필요. 공시=Article/Event로 흡수(ADR 0008)."""

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    def fetch_recent(self, page_count: int = 20) -> list[dict[str, Any]]:
        if not self._api_key:
            return []  # 키 없으면 스킵 — opendart 발급 후 활성화
        resp = httpx.get(
            "https://opendart.fss.or.kr/api/list.json",
            params={"crtfc_key": self._api_key, "page_count": page_count},
            timeout=30,
        )
        data = resp.json()
        docs: list[dict[str, Any]] = []
        for item in data.get("list", []):
            rcept = item.get("rcept_no", "")
            docs.append({
                "title": f"{item.get('corp_name', '')} {item.get('report_nm', '')}".strip(),
                "body": str(item.get("report_nm", "")),
                "source_url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept}",
                "license": "DART",
                "published_at": _dart_ts(str(item.get("rcept_dt", ""))),
            })
        return docs


# ── 거시 지표 (ECOS·FRED) → MacroIndicator 이벤트 표준 ──
# 표준: {name, value, unit, as_of(ISO UTC), source, source_url}. 가드레일: source_url 필수.

class EcosClient:
    """한국은행 ECOS(ecos.bok.or.kr, 무료 키) — 기준금리·환율·물가 등 거시 사실."""

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    def fetch(self, indicators: list[dict[str, str]]) -> list[dict[str, Any]]:
        """indicators = [{name, stat_code, cycle, item_code?, unit?}]. 각 지표 최신 1건.

        키 없으면 스킵. 값 조작 없이 API의 DATA_VALUE 그대로(float 변환만).
        ECOS는 오름차순 반환 → 최근 창을 조회해 rows[-1]이 최신이 되게 한다.
        주기별 날짜 포맷: D=YYYYMMDD, M=YYYYMM, Y=YYYY.
        """
        if not self._api_key:
            return []
        today = datetime.now(timezone.utc).date()
        out: list[dict[str, Any]] = []
        for ind in indicators:
            code, cycle = ind["stat_code"], ind.get("cycle", "M")
            if cycle == "D":
                start = (today - timedelta(days=45)).strftime("%Y%m%d")
                end = today.strftime("%Y%m%d")
            elif cycle == "Y":
                start, end = str(today.year - 5), str(today.year)
            else:  # M (기본)
                start = f"{today.year - 1}{today.month:02d}"
                end = f"{today.year}{today.month:02d}"
            url = (
                f"https://ecos.bok.or.kr/api/StatisticSearch/{self._api_key}"
                f"/json/kr/1/100/{code}/{cycle}/{start}/{end}"
            )
            resp = httpx.get(url, timeout=30)
            if resp.status_code != 200:
                continue
            rows = resp.json().get("StatisticSearch", {}).get("row", [])
            if ind.get("item_code"):
                rows = [r for r in rows if r.get("ITEM_CODE1") == ind["item_code"]]
            if not rows:
                continue
            row = rows[-1]  # 오름차순 → 최신 관측
            try:
                value = float(row["DATA_VALUE"])
            except (KeyError, ValueError):
                continue
            out.append({
                "name": ind["name"],
                "value": value,
                "unit": ind.get("unit", str(row.get("UNIT_NAME", ""))),
                "as_of": _ecos_ts(str(row.get("TIME", ""))),
                "source": "ECOS",
                "source_url": f"https://ecos.bok.or.kr/#/StatisticsSearch?statCode={code}",
            })
        return out


def _ecos_ts(t: str) -> str:
    """ECOS TIME(YYYYMM/YYYYMMDD/YYYY) → ISO UTC."""
    if len(t) == 6 and t.isdigit():
        return f"{t[:4]}-{t[4:6]}-01T00:00:00+00:00"
    if len(t) == 8 and t.isdigit():
        return f"{t[:4]}-{t[4:6]}-{t[6:]}T00:00:00+00:00"
    if len(t) == 4 and t.isdigit():
        return f"{t}-01-01T00:00:00+00:00"
    return datetime.now(timezone.utc).isoformat()


class FredClient:
    """FRED(api.stlouisfed.org, 무료 키) — 미 거시(연방기금금리·CPI 등)."""

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key

    def fetch(self, indicators: list[dict[str, str]]) -> list[dict[str, Any]]:
        """indicators = [{name, series_id, unit?}]. 각 최신 관측 1건. 키 없으면 스킵."""
        if not self._api_key:
            return []
        out: list[dict[str, Any]] = []
        for ind in indicators:
            series = ind["series_id"]
            resp = httpx.get(
                "https://api.stlouisfed.org/fred/series/observations",
                params={
                    "series_id": series, "api_key": self._api_key, "file_type": "json",
                    "sort_order": "desc", "limit": "1",
                },
                timeout=30,
            )
            if resp.status_code != 200:
                continue
            obs = resp.json().get("observations", [])
            if not obs or obs[0].get("value") in (None, "", "."):
                continue
            try:
                value = float(obs[0]["value"])
            except (KeyError, ValueError):
                continue
            out.append({
                "name": ind["name"],
                "value": value,
                "unit": ind.get("unit", ""),
                "as_of": f"{obs[0].get('date', '')}T00:00:00+00:00",
                "source": "FRED",
                "source_url": f"https://fred.stlouisfed.org/series/{series}",
            })
        return out
