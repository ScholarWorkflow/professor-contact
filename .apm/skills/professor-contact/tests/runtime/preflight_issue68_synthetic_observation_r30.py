import hashlib
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import preflight_issue68_environment_r30 as p

output = Path(sys.argv[2])
service_root = Path(sys.argv[3])
consumer = output / 'consumer'
consumer.mkdir()
before = p.runner.capture_eval_service_provenance(service_root)
p.write(output / 'service.before.json', before)
expected, command, input_path, observer, child = p.create_synthetic(output)
fixed = {str(path): p.digest(path) for path in (input_path, observer, child)}
prompt = ('这是环境预检。只执行下列完整命令一次，禁止其他命令、业务技能、代理委派、教授业务及任何文件修改。'
          '无需读取或改写脚本，不要打印预期对象代替命令。命令：\n' + command)
request = p.build_request(consumer, prompt)
request['timeout'] = 180
p.write(output / 'request.json', request)
p.write(output / 'manifest.json', {'expected': expected, 'command': command, 'fixed_before': fixed,
    'source_sha256': p.digest(__file__), 'preflight_sha256': p.digest(p.__file__),
    'formal_case_started': False, 'consumer_kind': 'empty_synthetic_consumer_no_product_install'})
result = {'state': 'PREFLIGHT_INCOMPLETE', 'formal_case_started': False,
          'installation_status': 'NOT_ATTEMPTED', 'scope': 'synthetic_observation_only'}
try:
    p.runner.base.progress('一次纯合成请求开始，最长180秒')
    req = urllib.request.Request(f"http://127.0.0.1:{before['service']['port']}/eval",
        json.dumps(request).encode(), {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=210) as response:
        raw = response.read()
    (output / 'response.json').write_bytes(raw)
    parsed = json.loads(raw)
    p.write(output / 'actual-request-configuration.json', p.request_configuration(request, parsed))
    observation = p.verify_observation(parsed, expected, command)
    p.write(output / 'observation.json', observation)
    after = p.runner.capture_eval_service_provenance(service_root, before['eval_server']['sha'])
    p.write(output / 'service.after.json', after)
    actual = {str(path): p.digest(path) for path in (input_path, observer, child)}
    integrity = {'fixed_before': fixed, 'fixed_after': actual,
                 'consumer_empty': not any(consumer.iterdir()),
                 'service_unchanged': p.runner.same_service(before, after)}
    p.write(output / 'integrity.json', integrity)
    if fixed != actual or not integrity['consumer_empty'] or not integrity['service_unchanged']:
        raise ValueError('synthetic_integrity_changed')
    result['observation'] = observation
    result['state'] = ('SYNTHETIC_OBSERVATION_READY' if observation['status'] == 'OBSERVATION_VERIFIED'
                       else 'PREFLIGHT_INCOMPLETE')
except Exception as exc:
    result['reason'] = str(exc)
    result['error_type'] = type(exc).__name__
finally:
    p.write(output / 'result.json', result)
    p.runner.base.progress('纯合成观察结束：' + result['state'])
raise SystemExit(0 if result['state'] == 'SYNTHETIC_OBSERVATION_READY' else 1)
