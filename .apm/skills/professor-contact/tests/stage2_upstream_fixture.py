"""Real Stage-0/1/2 prerequisites; never synthesize an identity proof."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from gate2_evidence import TestPreparationError

ROOT = Path(__file__).parents[1]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _prepare_stage2_proof(run_cli, facts_path):
    facts_path = Path(facts_path)
    facts = json.loads(facts_path.read_text())
    program_root = Path(facts['program_root'])
    professor_dir = Path(facts['professor_dir'])
    target = professor_dir / '套磁目标.json'
    if not target.exists():
        directions = []
        for item in facts['directions']:
            keys = item.get('provisional_member_keys') or item.get('member_keys') or []
            members = [{'item_key': key, 'preview_confidence': 'high'} for key in keys]
            directions.append({
                'direction_id': item.get('direction_id') or item['collection_key'],
                'name_ja': item['name_ja'], 'name_zh': item.get('name_zh', item['name_ja']),
                'summary_zh': item.get('summary_zh', '合成测试方向'),
                'members': members, 'member_fingerprint': digest({'version': '1', 'members': members}),
                'representatives': [], 'low_confidence_count': 0, 'coverage_share': 1.0,
            })
        counts = Counter(m['item_key'] for d in directions for m in d['members'])
        preview = {
            'schema_version': 1, 'professor': facts['professor'],
            'direction_id_version': 'members-v1', 'membership_mode': 'overlap_allowed',
            'membership_coverage': {'assigned_unique_members': len(counts),
                                    'membership_edges': sum(counts.values()),
                                    'overlap_member_count': sum(n > 1 for n in counts.values()),
                                    'overlap_members': sorted(k for k, n in counts.items() if n > 1),
                                    'unassigned_mountable_count': 0},
            'preview_fingerprint': digest(directions), 'preview_fingerprint_version': 'preview-v1',
            'coverage': 1.0, 'data_confidence': 'high', 'directions': directions,
        }
        preview_path = professor_dir / '方向预筛.json'
        write_json(preview_path, preview)
        selection = {'direction_ids': [d['direction_id'] for d in directions],
                     'notes': {d.get('direction_id') or d['collection_key']: d.get('user_note', '')
                               for d in facts['directions']}}
        selection_path = facts_path.with_name(facts_path.stem + '-selection.json')
        write_json(selection_path, selection)
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/contact_targets.py'),
                                 'bootstrap', '--program-root', str(program_root),
                                 '--preview', str(preview_path), '--selection-file', str(selection_path)],
                                text=True, capture_output=True)
        if result.returncode != 0:
            raise AssertionError(f'Stage-0 fixture bootstrap failed: {result.stdout} {result.stderr}')
        catalog = {'professor': {'name': facts['professor']},
                   'papers': [{**p, 'pdf_status': 'downloaded' if p.get('has_pdf') else 'pending'}
                              for p in facts['papers']]}
        write_json(professor_dir / 'papers.json', catalog)
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/contact_stage1.py'),
                                 'build', '--program-root', str(program_root),
                                 '--target-file', str(target)], text=True, capture_output=True)
        if result.returncode != 0:
            raise AssertionError(f'Stage-1 fixture build failed: {result.stdout} {result.stderr}')
    params = facts.get('params', {})
    arguments = ['stage2-preflight', '--program-root', program_root,
                 '--professor', facts['professor'], '--target-file', target,
                 '--paper-analysis', params.get('paper_analysis', 'relevant'),
                 '--gap-scope', params.get('gap_scope', 'selected_direction'),
                 '--freshness-scope', params.get('freshness_scope', 'shortlist')]
    if params.get('max_relevant_papers') is not None:
        arguments.extend(['--max-relevant-papers', params['max_relevant_papers']])
    result = run_cli(*arguments)
    if result.returncode != 0:
        raise AssertionError(f'Stage-2 fixture preflight failed: {result.stdout} {result.stderr}')
    proof = json.loads(result.stdout)
    if proof['status'] != 'ok':
        raise AssertionError(f'Stage-2 fixture preflight not ready: {proof}')
    if facts['current_year'] != proof['preflight_inputs']['current_year']:
        raise AssertionError('business fixture year differs from real preflight year')
    proof_path = facts_path.with_name(facts_path.stem + '-preflight.json')
    write_json(proof_path, proof)
    facts['stage2_preflight'] = {'preflight_id': proof['preflight_id']}
    write_json(facts_path, facts)
    return proof_path


def prepare_stage2_proof(run_cli, facts_path):
    """Build legal upstream state; failures are invalid prerequisites for the downstream proof."""
    try:
        return _prepare_stage2_proof(run_cli, facts_path)
    except TestPreparationError:
        raise
    except Exception as exc:
        raise TestPreparationError(
            f'Stage-2 prerequisite preparation failed: {type(exc).__name__}: {exc}'
        ) from exc


def _ensure_stage2_proof(run_cli, facts_path):
    facts_path = Path(facts_path)
    proof = facts_path.with_name(facts_path.stem + '-preflight.json')
    facts = json.loads(facts_path.read_text())
    if not proof.exists() or not facts.get('stage2_preflight'):
        proof = prepare_stage2_proof(run_cli, facts_path)
    return Path(proof)


def _prepare_consumption(run_cli, facts_path, proof_path):
    """Freeze this fixture's declared sources before the real plan/finalize."""
    facts_path = Path(facts_path)
    facts = json.loads(facts_path.read_text())
    reference = (facts.get('stage2_preflight') or {}).get('consumption')
    if isinstance(reference, dict) and reference.get('file'):
        companion_path = Path(reference['file'])
        if companion_path.is_file():
            try:
                companion = json.loads(companion_path.read_text())
            except (OSError, ValueError):
                companion = None
            if isinstance(companion, dict) and not companion.get('stage2_plan'):
                return subprocess.CompletedProcess(
                    [], 0,
                    json.dumps({'status': 'ok',
                                'consumption_file': str(companion_path),
                                'run_id': companion.get('run_id'),
                                'sources_sha256': companion.get('sources_sha256')}),
                    '')
    run_dir = facts_path.with_name(facts_path.stem + '-run')
    suffix = 0
    while run_dir.exists():
        suffix += 1
        run_dir = facts_path.with_name(f"{facts_path.stem}-run-{suffix}")
    run_dir.mkdir()
    sources_path = run_dir / 'source-declarations.json'
    write_json(sources_path, {'papers': facts.get('papers', []),
                              'current_year': facts.get('current_year')})
    target = Path(facts['professor_dir']) / '套磁目标.json'
    result = run_cli('stage2-consumption-prepare',
                     '--program-root', facts['program_root'],
                     '--professor', facts['professor'],
                     '--target-file', target,
                     '--sources-file', sources_path,
                     '--preflight-file', proof_path,
                     '--run-dir', run_dir)
    if result.returncode != 0:
        return result
    payload = json.loads(result.stdout)
    if payload.get('status') != 'ok':
        return result
    facts = json.loads(facts_path.read_text())
    facts.setdefault('stage2_preflight', {})['consumption'] = {
        'file': payload['consumption_file'], 'version': 1,
        'run_id': payload['run_id'], 'sources_sha256': payload['sources_sha256'],
    }
    write_json(facts_path, facts)
    return result


def prepare_consumption(run_cli, facts_path, proof_path=None):
    """Public fixture entry: freeze the facts' declared sources before plan/resolve."""
    facts_path = Path(facts_path)
    proof = Path(proof_path) if proof_path is not None \
        else _ensure_stage2_proof(run_cli, facts_path)
    return _prepare_consumption(run_cli, facts_path, proof)


def run_bound_stage2_plan(run_cli, facts_path):
    facts_path = Path(facts_path)
    proof = _ensure_stage2_proof(run_cli, facts_path)
    prepared = _prepare_consumption(run_cli, facts_path, proof)
    if prepared.returncode != 0:
        return prepared
    payload = json.loads(prepared.stdout)
    if payload.get('status') != 'ok':
        return prepared
    run_dir = Path(payload['consumption_file']).parent
    return run_cli('stage2-plan', '--facts', facts_path,
                   '--preflight-file', proof, '--run-dir', run_dir)


def _results_argument(arguments):
    for index, value in enumerate(arguments):
        if value == '--results' and index + 1 < len(arguments):
            return arguments[index + 1]
    return None


def run_bound_stage2_finalize(run_cli, facts_path, *arguments):
    facts_path = Path(facts_path)
    facts_before = facts_path.read_bytes()
    proof = _ensure_stage2_proof(run_cli, facts_path)
    facts = json.loads(facts_path.read_text())
    reference = (facts.get('stage2_preflight') or {}).get('consumption')
    companion_path = Path(reference['file']) if isinstance(reference, dict) \
        and reference.get('file') else None
    companion = None
    if companion_path is not None and companion_path.is_file():
        try:
            companion = json.loads(companion_path.read_text())
        except (OSError, ValueError):
            companion = None
    sealed = isinstance(companion, dict) and isinstance(companion.get('results'), dict)
    has_plan = isinstance(companion, dict) and isinstance(companion.get('stage2_plan'), dict)
    if not has_plan or sealed:
        planned = run_bound_stage2_plan(run_cli, facts_path)
        if planned.returncode != 0:
            return planned
        payload = json.loads(planned.stdout)
        if payload.get('status') != 'ok':
            return planned
        facts = json.loads(facts_path.read_text())
        reference = (facts.get('stage2_preflight') or {}).get('consumption')
        companion_path = Path(reference['file']) if isinstance(reference, dict) \
            and reference.get('file') else None
    results = _results_argument(arguments)
    if companion_path is not None and results:
        sealed_result = run_cli('stage2-consumption-seal-results',
                                '--run-dir', companion_path.parent,
                                '--results-dir', results)
        if sealed_result.returncode != 0:
            return sealed_result
        sealed_payload = json.loads(sealed_result.stdout)
        if sealed_payload.get('status') != 'ok':
            return sealed_result
    result = run_cli('stage2-finalize', '--facts', facts_path,
                     '--preflight-file', proof, *arguments)
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        payload = {}
    if payload.get('status') != 'ok':
        facts_path.write_bytes(facts_before)
    return result
