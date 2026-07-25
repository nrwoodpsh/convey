"""LLM 관계추출 — 하이브리드 추출의 'LLM 절반'. 라운드①.

기사 + 규칙 태깅된 엔티티 → (subject, edge, object) 관계 후보를 로컬 LLM으로 추출.
환각 방지: (1) 프롬프트로 허용 엔티티·정해진 엣지타입만 요구, (2) 결과에서 허용 밖은 폐기.
LLM은 주입(테스트=스텁, 운영=llm-inference→Ollama). 수치는 만들지 않음(사실은 Postgres).
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field

EDGE_TYPES: tuple[str, ...] = (
    "BELONGS_TO", "HAS_EVENT", "COMPETES", "SUPPLIES", "AFFECTS",   # 기존 5
    "PARTNERS_WITH", "AFFILIATE_OF", "BENEFITS_FROM", "HURT_BY",    # 확장(협력·계열·수혜·타격)
    "PRODUCES", "ACQUIRES", "REGULATES",                            # 확장(생산·인수·규제)
)


@dataclass
class Relation:
    subject: str
    edge: str
    object: str


def build_prompt(text: str, allowed_entities: list[str]) -> str:
    ents = ", ".join(allowed_entities)
    edges = ", ".join(EDGE_TYPES)
    return (
        "다음 기사에서 엔티티 간 관계만 JSON 배열로 추출하라.\n"
        f"허용 엔티티: {ents}\n"
        f"허용 엣지: {edges}\n"
        '형식: [{"subject":"...","edge":"...","object":"..."}]\n'
        "허용 엔티티/엣지만 사용. 없으면 []. 설명 없이 JSON만 출력.\n\n"
        f"기사:\n{text}"
    )


def _parse(raw: str) -> list[Relation]:
    """LLM 응답에서 JSON 배열만 관대하게 파싱(설명·<think> 등 감싸도 추출)."""
    match = re.search(r"\[.*\]", raw, re.S)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    out: list[Relation] = []
    for item in data:
        if isinstance(item, dict) and {"subject", "edge", "object"} <= item.keys():
            out.append(Relation(str(item["subject"]), str(item["edge"]), str(item["object"])))
    return out


def extract_relations(
    text: str, allowed_entities: list[str], llm: Callable[[str], str]
) -> list[Relation]:
    """LLM 추출 → 허용 엔티티·엣지로 필터. 허용 밖 엔티티·엣지는 폐기(환각 방지)."""
    allowed = set(allowed_entities)
    candidates = _parse(llm(build_prompt(text, allowed_entities)))
    return [
        r
        for r in candidates
        if r.subject in allowed and r.object in allowed and r.edge in EDGE_TYPES
    ]


# ── 개방형 NER(엔티티+관계 1콜, 라운드㉚) + 온톨로지 확장(㉟) ──
ENTITY_TYPES: tuple[str, ...] = (
    "기업", "인물", "사건", "기관", "섹터",   # 기존 5
    "제품", "테마", "정책", "국가",           # 확장 4
)
ENTITY_STOPWORDS: frozenset[str] = frozenset({
    "정부", "시장", "기업", "회사", "경제", "산업", "국내", "해외", "우리", "관련", "이번",
    "오늘", "내년", "올해", "사업", "서비스", "기술", "투자", "실적",
    # ㉟ 보강 — 일반 조직·집합어(노조 COMPETES 오염 등 차단)
    "노조", "노사", "이동통신사", "당국", "업계", "고객", "소비자", "국민", "지자체",
})
ENTITY_MIN_LEN = 2

# 엣지 domain/range 제약(㉟) — (주어 타입, 목적어 타입). 빈 tuple=제한 없음. 위반 폐기.
EDGE_DOMAIN_RANGE: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "BELONGS_TO":    (("기업",), ("섹터",)),
    "HAS_EVENT":     (("기업",), ("사건",)),
    "COMPETES":      (("기업",), ("기업",)),
    "SUPPLIES":      (("기업",), ("기업",)),
    "AFFECTS":       ((), ()),  # 일반 영향 — 제한 없음
    "PARTNERS_WITH": (("기업",), ("기업",)),
    "AFFILIATE_OF":  (("기업",), ("기업",)),
    "BENEFITS_FROM": (("기업",), ("정책", "사건", "테마")),
    "HURT_BY":       (("기업",), ("정책", "사건")),
    "PRODUCES":      (("기업",), ("제품",)),
    "ACQUIRES":      (("기업",), ("기업",)),
    "REGULATES":     (("기관",), ("기업", "섹터")),
}

# 사건(Event) 속성(㉟) — 새 노드/엣지 대신 속성으로.
EVENT_TYPES: tuple[str, ...] = (
    "실적", "유상증자", "무상증자", "자사주", "배당", "감자", "인수합병",
    "수주", "신제품", "증설", "소송", "파업", "급등락",
)


@dataclass
class TypedEntity:
    """확장 추출 엔티티(㉟) — 이름 + 타입(+ 사건 속성). 레거시(문자열)는 type="" 로."""

    name: str
    type: str = ""            # ENTITY_TYPES 중 하나(빈 문자열=미상/레거시)
    event_type: str = ""      # type=="사건"일 때(EVENT_TYPES)
    direction: str = ""       # 긍정/부정/중립(호재/악재)

# ── 요약 선행 NER(㉛, ADR 0015) ──
SUMMARY_THRESHOLD = 1500  # 본문 char > 이 값이면 요약 선행. 이하는 원문 그대로 NER.
SUMMARY_NUM_PREDICT = 256  # 요약 호출 출력 토큰 상한(호출 경계에서 바인딩) — 타임아웃 방지.


@dataclass
class Graph:
    """개방형 추출 결과 — 엔티티 + 관계(㉚). 타입·사건 속성은 확장(㉟, 하위호환 기본값)."""

    entities: list[str]
    relations: list[Relation]
    types: dict[str, str] = field(default_factory=dict)               # name → 엔티티 타입
    events: dict[str, tuple[str, str]] = field(default_factory=dict)  # name → (event_type, direction)


def _normalize_entity(name: str) -> str:
    """엔티티 표기 정리 — 공백·감싼 따옴표/괄호 제거. (완전 개체연결은 후속.)"""
    n = name.strip().strip("'\"“”()[]{}〈〉《》").strip()
    return n


def build_graph_prompt(text: str) -> str:
    types = ", ".join(ENTITY_TYPES)
    edges = ", ".join(EDGE_TYPES)
    events = ", ".join(EVENT_TYPES)
    return (
        "다음 기사에서 엔티티와 관계를 JSON 객체로 추출하라.\n"
        f"엔티티 종류(type): {types}. 반드시 기사에 실제로 나온 표현만.\n"
        f"사건이면 event_type({events})와 direction(긍정/부정/중립)도.\n"
        f"허용 엣지(edge): {edges}. 엣지는 타입에 맞게(예: BELONGS_TO는 기업→섹터, HAS_EVENT는 기업→사건).\n"
        '형식: {"entities":[{"name":"..","type":".."}],'
        '"relations":[{"subject":"..","edge":"..","object":".."}]}\n'
        "기사에 없는 것은 만들지 말 것. 설명 없이 JSON만 출력.\n\n"
        f"기사:\n{text}"
    )


def _parse_graph(raw: str) -> tuple[list[TypedEntity], list[Relation]]:
    """LLM 응답에서 {entities, relations} 파싱(㉟). 엔티티는 {name,type,...} 또는 문자열(레거시)."""
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return [], []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return [], []
    ents: list[TypedEntity] = []
    for e in data.get("entities", []):
        if isinstance(e, str):  # 레거시 — 이름만(type 미상)
            ents.append(TypedEntity(name=e))
        elif isinstance(e, dict) and "name" in e:
            ents.append(TypedEntity(
                name=str(e["name"]), type=str(e.get("type", "")),
                event_type=str(e.get("event_type", "")), direction=str(e.get("direction", "")),
            ))
    rels: list[Relation] = []
    for item in data.get("relations", []):
        if isinstance(item, dict) and {"subject", "edge", "object"} <= item.keys():
            rels.append(Relation(str(item["subject"]), str(item["edge"]), str(item["object"])))
    return ents, rels


def extract_graph(
    text: str,
    seed_entities: list[str],
    llm: Callable[[str], str],
    *,
    verify_text: str | None = None,
) -> Graph:
    """개방형 추출(㉚) — 엔티티+관계 1콜. 환각 통제: 본문 실재(substring)·정규화·스톱워드·엣지 제한.

    seed_entities(사전=고정확)는 검증 없이 신뢰(news-feed가 본문 매칭으로 뽑음). LLM 엔티티는 검증.
    verify_text(㉛): NER 입력은 text, 환각 검증은 verify_text(없으면 text). 요약 경로에서
    text=요약·verify_text=원문 → 엔티티는 원문 실재만 채택(요약 환각 폐기, 알파1 보존).
    """
    verify = verify_text if verify_text is not None else text
    raw_ents, raw_rels = _parse_graph(llm(build_graph_prompt(text)))
    verified: set[str] = set()
    types: dict[str, str] = {}                    # name → 타입(미상="")
    events: dict[str, tuple[str, str]] = {}       # name → (event_type, direction)
    for e in raw_ents:
        raw = e.name.strip()
        if not (raw and raw in verify):           # 환각컷: 원문 실재
            continue
        if e.type and e.type not in ENTITY_TYPES:  # ㉟ 타입 검증(허용 밖 폐기, 미상은 통과)
            continue
        n = _normalize_entity(raw)
        if len(n) >= ENTITY_MIN_LEN and n not in ENTITY_STOPWORDS:
            verified.add(n)
            types[n] = e.type
            if e.type == "사건" and (e.event_type or e.direction):
                events[n] = (e.event_type, e.direction)
    # 사전 seed 합집(seed는 이미 본문 매칭 — 고정확, 타입 미상)
    for s in seed_entities:
        verified.add(s)
        types.setdefault(s, "")
    rels: list[Relation] = []
    for r in raw_rels:
        s, o = r.subject.strip(), r.object.strip()
        if not (s in verified and o in verified and r.edge in EDGE_TYPES):
            continue
        if not _edge_ok(r.edge, types.get(s, ""), types.get(o, "")):  # ㉟ domain/range
            continue
        rels.append(Relation(s, r.edge, o))
    return Graph(entities=sorted(verified), relations=rels, types=types, events=events)


def _edge_ok(edge: str, subj_type: str, obj_type: str) -> bool:
    """엣지-양끝 타입 제약(㉟). 양끝 타입을 알 때만 검사(미상은 허용 — 하위호환·seed)."""
    dr = EDGE_DOMAIN_RANGE.get(edge)
    if dr is None:
        return True
    dom, rng = dr
    if dom and subj_type and subj_type not in dom:
        return False
    if rng and obj_type and obj_type not in rng:
        return False
    return True


def build_summary_prompt(text: str) -> str:
    """요약 프롬프트(㉛) — 핵심 사실·엔티티 보존, 새 정보 추가 금지. 짧게(3~5문장)."""
    return (
        "다음 기사를 핵심 사실과 등장 엔티티(기업·인물·사건·기관·섹터) 중심으로 "
        "3~5문장으로 요약하라. 기사에 없는 내용은 추가하지 말 것. 설명 없이 요약만 출력.\n\n"
        f"기사:\n{text}"
    )


def summarize(text: str, llm: Callable[[str], str]) -> str:
    """본문 요약(㉛) — 로컬 Ollama. llm은 출력 상한(SUMMARY_NUM_PREDICT)이 바인딩된 caller."""
    return llm(build_summary_prompt(text)).strip()


def extract_article_graph(
    body: str,
    seed_entities: list[str],
    llm: Callable[[str], str],
    llm_summary: Callable[[str], str],
    *,
    summary_threshold: int = SUMMARY_THRESHOLD,
) -> Graph:
    """오케스트레이션(㉛) — 긴 본문은 요약 후 NER(원문검증), 짧은 본문은 원문 NER.

    긴 본문을 통째로 NER하면 로컬 LLM 생성이 타임아웃 → 요약(출력 상한)으로 선행 축약.
    seed_entities는 항상 원문 기준(news-feed 태깅). 요약 경로도 검증은 원문(알파1).
    """
    if len(body) <= summary_threshold:
        return extract_graph(body, seed_entities, llm)
    summary = summarize(body, llm_summary)
    return extract_graph(summary, seed_entities, llm, verify_text=body)
