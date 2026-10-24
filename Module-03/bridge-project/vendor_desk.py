"""Module 03 Bridge: Vendor Onboarding Desk (educational screening only)."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
from registry_tools import (
    sanctions_screen, gleif_lookup, NO_RECORDS, LOOKUP_UNAVAILABLE,
)
from search_tools import web_search

BASE = Path(__file__).resolve().parent
load_dotenv(BASE / '.env')
load_dotenv(BASE.parent.parent / '.env')
MAX_LOOKUPS = 9
SANCTIONS_THRESHOLD = 0.93
# Spend the scarce identity budget on larger risks; keep this small supplier
# explicitly unverified rather than quietly pretending we checked it.
DEFERRED_NAME = 'C & V Works ApS'


class State(TypedDict):
    request: str
    queue: list[dict]
    completed: list[dict]
    current: dict
    evidence: dict
    used: int
    memo: str
    skipped: list[str]
    queries: list[str]


class Wording(BaseModel):
    reason: str = Field(description='Concise explanation using supplied evidence only')


def parse_request(text: str) -> list[dict]:
    """Extract vendor rows from the fenced list in Finance's email."""
    blocks = re.findall(r'```\s*\n(.*?)\n```', text, re.S)
    if not blocks:
        raise ValueError('No supplier list found in REQUEST.md')
    suppliers = []
    for line in blocks[0].splitlines():
        if '—' not in line:
            continue
        name, details = (part.strip() for part in line.split('—', 1))
        if not name:
            continue
        kind, _, country = details.rpartition(',')
        suppliers.append({'name': name, 'category': kind.strip(), 'country': country.strip()})
    if len(suppliers) != 7:
        raise ValueError(f'Expected seven suppliers in REQUEST.md, got {len(suppliers)}')
    return suppliers


def ofac_matches(report: str) -> list[tuple[float, str, str]]:
    result = []
    for line in report.splitlines():
        match = re.match(r'^\s*(1\.00|0\.\d+)\s+(.+?)\s+\[programme: (.+?)\]', line)
        if match:
            result.append((float(match.group(1)), match.group(2), match.group(3)))
    return result


def normalized(s: str) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', s.casefold()).strip()


def exact_record(report: str, name: str) -> list[str]:
    records = []
    for line in report.splitlines():
        if line.startswith('Legal name:'):
            actual = line.split(' | LEI:', 1)[0].removeprefix('Legal name:').strip()
            if actual.casefold() == name.casefold():
                records.append(line)
    return records


def triage(state: State) -> dict:
    suppliers = parse_request(state['request'])
    # OFAC is obligatory for all seven and never uses the GLEIF budget.
    for s in suppliers:
        s['ofac'] = sanctions_screen(s['name'])
    # High-severity sanctions signal first, then ambiguous company names,
    # then other names; the small Danish supplier is intentionally deferred.
    priority = {
        'Al Wasel and Babel General Trading LLC': 100,
        'Siemens AG': 90,
        'Zorblax Trading FZE': 80,
        'Al Noor Cart Trading Company': 70,
        'Almarai Company': 60,
        'Maersk A/S': 50,
        DEFERRED_NAME: 0,
    }
    suppliers.sort(key=lambda s: -priority.get(s['name'], 10))
    print('TRIAGE:', ' -> '.join(s['name'] for s in suppliers))
    return {'queue': suppliers, 'completed': [], 'used': 0,
            'skipped': [], 'queries': [], 'memo': ''}


def lookup(query: str, state: State, evidence: dict) -> tuple[str, int, list[str]]:
    used = state['used'] + evidence.get('spent_here', 0)
    queries = state['queries'] + evidence.get('new_queries', [])
    if used >= MAX_LOOKUPS or query.casefold() in (q.casefold() for q in queries):
        return 'NOT_CHECKED_BUDGET_OR_DUPLICATE', used, queries
    used += 1
    queries.append(query)
    print(f'[GLEIF {used}/{MAX_LOOKUPS}] {query}', flush=True)
    answer = gleif_lookup(query)
    evidence['spent_here'] = evidence.get('spent_here', 0) + 1
    evidence.setdefault('new_queries', []).append(query)
    return answer, used, queries


def screen(state: State) -> dict:
    supplier = state['queue'][0]
    name = supplier['name']
    evidence = {'ofac': supplier['ofac']}
    if name == DEFERRED_NAME:
        evidence['gleif'] = 'NOT_CHECKED_BUDGET_PRIORITY'
        return {'current': supplier, 'evidence': evidence}

    first, _, _ = lookup(name, state, evidence)
    evidence['gleif'] = first
    if first == NO_RECORDS:
        evidence['web'] = web_search(name)

    # Three additional identity investigations where ambiguity is important.
    # Keep each lookup query distinct, and never exceed the global budget.
    followups = {
        'Siemens AG': ['Siemens Aktiengesellschaft', 'Siemens GmbH'],
        'Almarai Company': ['Almarai'],
    }
    evidence['additional'] = []
    for query in followups.get(name, []):
        if state['used'] + evidence.get('spent_here', 0) >= MAX_LOOKUPS:
            break
        response, _, _ = lookup(query, state, evidence)
        evidence['additional'].append((query, response))
    return {'current': supplier, 'evidence': evidence,
            'used': state['used'] + evidence.get('spent_here', 0),
            'queries': state['queries'] + evidence.get('new_queries', [])}


def decide(state: State) -> dict:
    supplier = state['current']
    name = supplier['name']
    ev = state['evidence']
    ofac = ev['ofac']
    register = ev['gleif']
    matches = ofac_matches(ofac)
    verdict = 'INSUFFICIENT'
    reason = ''
    action = ''

    if ofac == LOOKUP_UNAVAILABLE:
        reason = 'Mandatory sanctions screening was unavailable.'
        action = 'Hold payment and repeat sanctions screening before any release.'
    elif any(score >= SANCTIONS_THRESHOLD and normalized(listed) == normalized(name)
             for score, listed, _ in matches):
        hit = next(hit for hit in matches if hit[0] >= SANCTIONS_THRESHOLD
                   and normalized(hit[1]) == normalized(name))
        verdict = 'REJECT'
        reason = (f'OFAC SDN-listed name exact match (similarity {hit[0]:.2f}), '
                  f'programme {hit[2]}. Name screening requires Compliance identity confirmation.')
        action = 'Do not pay; escalate immediately to Legal/Compliance for definitive entity verification.'
    elif any(score >= SANCTIONS_THRESHOLD for score, _, _ in matches):
        verdict = 'CONDITIONS'
        hit = next(hit for hit in matches if hit[0] >= SANCTIONS_THRESHOLD)
        reason = f'Potential OFAC name match {hit[0]:.2f} against {hit[1]} ({hit[2]}).'
        action = 'Hold payment; Compliance must investigate the match and document clearance.'
    elif register == 'NOT_CHECKED_BUDGET_PRIORITY':
        reason = 'Identity lookup intentionally deferred to prioritize higher-risk suppliers.'
        action = 'Hold payment pending a GLEIF or official corporate-register identity check.'
    elif register == LOOKUP_UNAVAILABLE:
        reason = 'GLEIF registry was unavailable; identity not established.'
        action = 'Hold payment; obtain official company registration and verify the payee.'
    elif register == NO_RECORDS:
        web = ev.get('web', 'NO_RESULTS')
        if web not in ('NO_RESULTS', 'SEARCH_UNAVAILABLE', ''):
            verdict = 'CONDITIONS'
            reason = 'GLEIF returned NO_RECORDS; independent web references suggest existence but not payee identity.'
            action = 'Obtain incorporation certificate, registration number and beneficiary-bank verification.'
        else:
            reason = 'No LEI and no reliable independent record establishing this legal payee.'
            action = 'Hold payment; obtain official registry extract and company registration number.'
    else:
        exact = exact_record(register, name)
        if len(exact) != 1:
            verdict = 'CONDITIONS'
            reason = f'Identity ambiguous: {len(exact)} exact legal-name records; other matches are not the requested supplier.'
            action = 'Ask Procurement for exact LEI or registration number from invoice before payment.'
        elif ('entity status: ACTIVE' not in exact[0]
              or 'registration status: ISSUED' not in exact[0]):
            verdict = 'CONDITIONS'
            reason = 'The legal entity or LEI registration is not both ACTIVE and ISSUED.'
            action = 'Obtain current official registration evidence and resolve lapsed/retired status.'
        else:
            verdict = 'APPROVE'
            reason = 'One exact legal name with ACTIVE entity and ISSUED LEI registration; no strong OFAC name hit.'
            action = 'Eligible for Finance review; verify invoice beneficiary and standard payment controls.'

    # Model may clarify wording, but must not change the deterministic verdict.
    key = os.getenv('OPENROUTER_API_KEY')
    if key and reason:
        try:
            llm = ChatOpenAI(model='openai/gpt-4o-mini',
                             base_url='https://openrouter.ai/api/v1',
                             api_key=key, temperature=0, timeout=25, max_retries=1)
            response = llm.with_structured_output(Wording).invoke(
                f'Simplify the following reason for a finance manager in one sentence. '
                f'Preserve all concrete facts; add no facts. Supplier {name}. '
                f'Original: {reason}'
            )
            if response and response.reason.strip():
                reason = response.reason.strip()
        except Exception:
            pass

    result = {'name': name, 'verdict': verdict, 'reason': reason,
              'action': action, 'evidence': ev}
    print(f'[{verdict}] {name}', flush=True)
    skipped = list(state['skipped'])
    if register == 'NOT_CHECKED_BUDGET_PRIORITY':
        skipped.append(name)
    return {'completed': state['completed'] + [result],
            'queue': state['queue'][1:], 'skipped': skipped}


def router(state: State) -> str:
    return 'screen' if state['queue'] else 'write_memo'


def write_memo(state: State) -> dict:
    lines = [
        '# SUPPLIER REVIEW — Thursday payment run', '',
        f'**7 suppliers | {state["used"]}/{MAX_LOOKUPS} GLEIF lookups used**', '',
        'OFAC screening was attempted for every supplier and is outside the GLEIF budget.',
        'This educational screening is not a substitute for a legal compliance decision.', '',
    ]
    for item in state['completed']:
        ev = item['evidence']
        lines += [f'## {item["verdict"]} — {item["name"]}', '', item['reason'], '',
                  '**Rana:** ' + item['action'], '', '**GLEIF:**', '',
                  str(ev['gleif']), '', '**OFAC:**', '', str(ev['ofac']), '']
        if 'web' in ev:
            lines += ['**Web:**', '', str(ev['web']), '']
        for query, response in ev.get('additional', []):
            lines += [f'**Additional GLEIF lookup — {query}:**', '', str(response), '']
    lines += ['## NOT CHECKED (budget priority)', '']
    if state['skipped']:
        for supplier in state['skipped']:
            lines += [f'- **{supplier}:** Identity lookup not performed; payment remains held.']
    else:
        lines += ['- None.']
    lines += ['', f'**Lookup count:** {state["used"]} / {MAX_LOOKUPS}', '',
              '**Unresolved risk:** A name similarity match alone cannot prove legal identity; '
              'no payment should bypass beneficiary validation and applicable compliance review.', '']
    memo = '\n'.join(lines)
    (BASE / 'MEMO.md').write_text(memo, encoding='utf-8')
    print(f'MEMO saved: {BASE / "MEMO.md"}')
    return {'memo': memo}


def build_graph():
    graph = StateGraph(State)
    graph.add_node('triage', triage)
    graph.add_node('screen', screen)
    graph.add_node('decide', decide)
    graph.add_node('write_memo', write_memo)
    graph.set_entry_point('triage')
    graph.add_edge('triage', 'screen')
    graph.add_edge('screen', 'decide')
    graph.add_conditional_edges('decide', router,
                                {'screen': 'screen', 'write_memo': 'write_memo'})
    graph.add_edge('write_memo', END)
    return graph.compile()


def main() -> None:
    request = (BASE / 'REQUEST.md').read_text(encoding='utf-8')
    result = build_graph().invoke({
        'request': request, 'queue': [], 'completed': [], 'current': {},
        'evidence': {}, 'used': 0, 'memo': '', 'skipped': [], 'queries': [],
    }, config={'recursion_limit': 35})
    print(f'Completed {len(result["completed"])} suppliers; '
          f'{result["used"]} GLEIF lookups.')
    for item in result['completed']:
        print(item['verdict'], item['name'])


if __name__ == '__main__':
    main()
