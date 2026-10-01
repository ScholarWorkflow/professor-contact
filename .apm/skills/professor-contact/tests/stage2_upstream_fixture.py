"""Real Stage-0/1/2 prerequisites; never synthesize an identity proof."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).parents[1]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def prepare_stage2_proof(run_cli, facts_path):
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


def run_bound_stage2_plan(run_cli, facts_path):
    facts_path = Path(facts_path)
    proof = facts_path.with_name(facts_path.stem + '-preflight.json')
    facts = json.loads(facts_path.read_text())
    if not proof.exists() or not facts.get('stage2_preflight'):
        proof = prepare_stage2_proof(run_cli, facts_path)
    return run_cli('stage2-plan', '--facts', facts_path, '--preflight-file', proof)


def run_bound_stage2_finalize(run_cli, facts_path, *arguments):
    facts_path = Path(facts_path)
    proof = facts_path.with_name(facts_path.stem + '-preflight.json')
    facts = json.loads(facts_path.read_text())
    if not proof.exists() or not facts.get('stage2_preflight'):
        proof = prepare_stage2_proof(run_cli, facts_path)
    return run_cli('stage2-finalize', '--facts', facts_path, '--preflight-file', proof, *arguments)
