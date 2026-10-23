"""Build a new, clearly synthetic UI demo through the existing intake API."""
import argparse
from pathlib import Path
import time

from labflow.active_intake import register_source, scan_source
from labflow.intake_jobs import claim_job, complete_job, fail_job, respond
from labflow.store import Store


def build_demo(root, *, empty=False):
    root = Path(root).resolve()
    # Never point a demo writer at an existing input or state directory.
    root.mkdir(parents=True, exist_ok=False)
    inbox = root / 'input'
    inbox.mkdir()
    store = Store(root / 'state')
    register_source(store, 'DEMO-SYNTHETIC', inbox, synthetic=True, settle_seconds=1)
    if empty:
        return store.root
    clock = time.time()

    def accept(name, *, conflict=False, unread=False):
        nonlocal clock
        folder = inbox / name
        folder.mkdir()
        (folder / '의뢰서.txt').write_text(
            '제품: 휴대형 통신 기기 (합성 예시)\n의뢰 시장: US\n의뢰 목적: 개발 검토\n'
            '<img src=x onerror="window.uiInjected=true"> 원문은 실행하지 않습니다.\n', encoding='utf-8')
        if conflict:
            (folder / '보완 요청.txt').write_text('의뢰 시장: EU (합성 충돌 예시)\n', encoding='utf-8')
        if unread:
            (folder / '제품 설명.pdf').write_bytes(b'%PDF-synthetic-unparsed-fixture')
        clock += 10
        scan_source(store, 'DEMO-SYNTHETIC', now=clock)
        return scan_source(store, 'DEMO-SYNTHETIC', now=clock+1)['accepted'][-1]['intake_id']

    def claim():
        return claim_job(store, 'synthetic-ui-fixture', now=clock+2, lease_seconds=3600)

    def finish(intake_id, missing=(), conflict=False):
        job = claim()
        if job['intake_id'] != intake_id:
            raise RuntimeError('Unexpected fixture queue order')
        doc = next(item for item in job['documents'] if item['path'] == '의뢰서.txt')

        def fact(field, value, document, line, status='explicit'):
            return {'field': field, 'value': value, 'status': status, 'evidence': [{
                'path': document['path'], 'sha256': document['sha256'], 'line_start': line,
                'line_end': line, 'quote': document['text'].splitlines()[line-1], 'role': 'request'}]}

        facts = [fact('product_type', '휴대형 통신 기기', doc, 1, 'inferred'),
                 fact('market', 'US', doc, 2), fact('purpose', '개발 검토', doc, 3),
                 fact('features', '원문 HTML 안전 표시 확인', doc, 4, 'uncertain')]
        if conflict:
            other = next(item for item in job['documents'] if item['path'] == '보완 요청.txt')
            facts.append(fact('market', 'EU', other, 1))
        complete_job(store, job['job_id'], job['token'], {
            'schema_version': 1, 'producer': {'kind': 'fixture', 'name': 'DEV4-UI-001 synthetic fixture'},
            'identity': 'single', 'facts': facts, 'missing_fields': list(missing)}, now=clock+3)

    conflict_id = accept('01 · 의뢰 확인 — 시장 충돌', conflict=True, unread=True)
    finish(conflict_id, missing=['firmware', 'antenna_gain'], conflict=True)
    held = accept('02 · 검토 보류 — 사용자 요청')
    finish(held, missing=['firmware'])
    respond(store, 'DEMO-HOLD', 'defer', intake_id=held)
    failed = accept('03 · 분석 실패 — 재시도 한도')
    for _ in range(3):
        job = claim()
        if job['intake_id'] != failed:
            raise RuntimeError('Unexpected fixture failure queue')
        fail_job(store, job['job_id'], job['token'], now=clock+3)
    ready = accept('04 · 계획 연결 대기 — 접수 위임')
    finish(ready)
    respond(store, 'DEMO-PROCEED', 'proceed', intake_id=ready)
    answered = accept('05 · 사용자 답변 — 보완 확인')
    finish(answered, missing=['firmware'])
    respond(store, 'DEMO-ANSWER', 'answer', intake_id=answered, answers={'firmware': 'FW-DEMO-1 (합성 답변)'})
    incomplete = accept('06 · 자료 미완성 — 복사 대기')
    folder = inbox / '06 · 자료 미완성 — 복사 대기'
    (folder / '미완성.part').write_text('synthetic partial', encoding='utf-8')
    scan_source(store, 'DEMO-SYNTHETIC', now=clock+2)
    running = accept('07 · 분석 중 — 작업 임대 기록')
    job = claim()
    if job['intake_id'] != running:
        raise RuntimeError('Unexpected fixture active queue')
    accept('08 · 분석 대기 — 새 자료')
    return store.root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', help='New demo directory; existing directories are rejected')
    parser.add_argument('--empty', action='store_true')
    args = parser.parse_args()
    workspace = build_demo(args.directory, empty=args.empty)
    print(f'Synthetic UI workspace: {workspace}')
    print('No model, hardware, external upload or message was used.')


if __name__ == '__main__':
    main()
