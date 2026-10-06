"""One non-business request to characterize bounded root file operations."""
import hashlib
import json
import shlex
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import preflight_issue68_environment_r30 as p
import issue68_lifecycle as lifecycle

output = Path(sys.argv[2])
service_root = Path(sys.argv[3])
consumer = output / 'consumer'
consumer.mkdir()
expected = {'marker': '生命周期合成输入', 'value': '原编号::空 格', 'choices': [2, 1, 2]}
target = consumer / 'request-owned-transfer.json'
sentinel = consumer / 'protected-other-request.json'
p.write(sentinel, {'marker': '另一请求保留数据'})
before = lifecycle.snapshot_tree(consumer)
before_service = p.runner.capture_eval_service_provenance(service_root)
p.write(output / 'service.before.json', before_service)
commands = [shlex.join(['printf', '%s', json.dumps(expected, ensure_ascii=False)]) + ' > ' + shlex.quote(str(target)),
            shlex.join(['cat', str(target)]), shlex.join(['rm', '--', str(target)])]
prompt = ('这是纯合成环境预检。依次分别执行以下三条完整命令，每条独立执行一次；不要合并、改写或新增命令。'
          '禁止业务技能、代理委派、教授业务及其他文件修改。命令如下：\n' + '\n'.join(commands))
request = p.build_request(consumer, prompt)
request['timeout'] = 180
p.write(output / 'request.json', request)
p.write(output / 'manifest.json', {'expected': expected, 'target': str(target), 'commands': commands,
    'protected': str(sentinel), 'entrypoint_sha256': p.digest(__file__),
    'helper_sha256': p.digest(lifecycle.__file__), 'before': before, 'formal_case_started': False})
result = {'state': 'PREFLIGHT_INCOMPLETE', 'formal_case_started': False,
          'installation_status': 'NOT_ATTEMPTED', 'scope': 'bounded_root_file_operations_only'}
try:
    p.runner.base.progress('真实有限文件操作合成请求开始，最长180秒')
    req = urllib.request.Request(f"http://127.0.0.1:{before_service['service']['port']}/eval",
        json.dumps(request).encode(), {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=210) as response:
        raw = response.read()
    (output / 'response.json').write_bytes(raw)
    parsed = json.loads(raw)
    p.write(output / 'actual-request-configuration.json', p.request_configuration(request, parsed))
    root = parsed.get('output', {}).get('thread_id')
    turn = parsed.get('output', {}).get('turn_id')
    generation = parsed.get('output', {}).get('runtime_generation')
    events = parsed.get('output', {}).get('app_server_events')
    if not root or not turn or generation is None or not isinstance(events, list):
        raise ValueError('actual_root_event_context_missing')
    previous, starts, completed = -1, {}, set()
    for event in events:
        seq = event.get('runtime_seq')
        if type(seq) is not int or seq <= previous or type(event.get('runtime_generation')) is not type(generation) \
                or event['runtime_generation'] != generation:
            raise ValueError('event_sequence_or_generation_invalid')
        previous = seq
        message = event.get('message', {})
        params = message.get('params', {})
        item = params.get('item', {})
        if item.get('type') != 'commandExecution':
            continue
        if params.get('threadId') != root or params.get('turnId') != turn:
            raise ValueError('command_root_or_turn_mismatch')
        identity = item.get('id')
        if not isinstance(identity, str) or not identity:
            raise ValueError('command_identity_missing')
        if message.get('method') == 'item/started':
            if identity in starts:
                raise ValueError('duplicate_command_started')
            starts[identity] = seq
        elif message.get('method') == 'item/completed':
            if identity not in starts or identity in completed or item.get('status') != 'completed' \
                    or item.get('exitCode') != 0:
                raise ValueError('command_completion_invalid')
            completed.add(identity)
    if len(completed) != 3 or set(starts) != completed:
        raise ValueError('exact_three_command_pairs_missing')
    calls = lifecycle._commands(parsed)
    operations = []
    for call in calls:
        operation = lifecycle.file_operation(call['command'])
        if operation and call['thread'] == root and call['exit_code'] == 0:
            operations.append({**call, **operation})
    p.write(output / 'operations.json', operations)
    after = lifecycle.snapshot_tree(consumer)
    after_service = p.runner.capture_eval_service_provenance(service_root, before_service['eval_server']['sha'])
    p.write(output / 'service.after.json', after_service)
    original_manifest = json.loads((output / 'manifest.json').read_text())
    integrity = {'before': before, 'after': after,
        'service_unchanged': p.runner.same_service(before_service, after_service),
        'helper_unchanged': p.digest(lifecycle.__file__) == original_manifest['helper_sha256'],
        'entrypoint_unchanged': p.digest(__file__) == original_manifest['entrypoint_sha256']}
    p.write(output / 'integrity.json', integrity)
    if before != after or not all(integrity[key] for key in
            ('service_unchanged', 'helper_unchanged', 'entrypoint_unchanged')):
        raise ValueError('synthetic_files_or_service_changed')
    if len(operations) != 3 or [op['operation'] for op in operations] != ['write', 'read', 'remove']:
        raise ValueError('bounded_root_file_operation_chain_unobservable')
    if any(op['paths'] != [str(target)] or op['start'] is None or op['start'] >= op['end']
           or type(op['generation']) is not type(generation) or op['generation'] != generation for op in operations):
        raise ValueError('bounded_chain_association_invalid')
    if not (operations[0]['end'] < operations[1]['start'] < operations[1]['end'] < operations[2]['start']):
        raise ValueError('bounded_chain_order_invalid')
    if json.loads(operations[1]['output']) != expected:
        raise ValueError('actual_file_read_mismatch')
    if target.exists() or target.is_symlink():
        raise ValueError('owned_file_remains')
    result.update(state='SYNTHETIC_LIFECYCLE_READY', generation=generation,
                  operations=operations, actual_read=json.loads(operations[1]['output']),
                  before_absent=True, after_absent=True, protected_other_request_unchanged=True)
except Exception as exc:
    result['reason'] = str(exc)
    result['error_type'] = type(exc).__name__
finally:
    p.write(output / 'result.json', result)
    p.runner.base.progress('真实有限文件操作合成请求结束：' + result['state'])
raise SystemExit(0 if result['state'] == 'SYNTHETIC_LIFECYCLE_READY' else 1)
