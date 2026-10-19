"""CI gate: frozen historical evidence, full reporting, current-rule enforcement.

The original validator remains available in Git for reproducible historical replay.
This gate neither edits records nor treats a historical finding as resolved.
"""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import re

BASELINE='ci/baselines/learning-2026-10-19.json'
BASELINE_SHA256='df6468905aaac221a8869f50b5f8e5448c0ffcfc04f81b25b90ac5bc571c36a7'
ROOT=Path(__file__).resolve().parents[1]
# Reviewed upstream 0eec1ce: AGENTS16 adds CLAUDE_SPARTA_BRAIN; no other
# validation change. Keep the original baseline bytes and error inventory frozen.
APPROVED_VALIDATOR_SHA256='448ad31a0764512a5182a4abae8a7e44cc793801a37070fc32125b31a84009ce'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def pairs(items):
        result={}
        for key,value in items:
            if key in result: raise ValueError('duplicate JSON key')
            result[key]=value
        return result
    def invalid(value): raise ValueError('nonfinite JSON number')
    def finite(value):
        import math
        parsed=float(value)
        if not math.isfinite(parsed): raise ValueError('nonfinite JSON number')
        return parsed
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid,parse_float=finite)


def evaluate(root=ROOT,comparison_ref=None):
    root=Path(root)
    result={'passed':False,'historical_errors':[],'current_warnings':[],'current_report':'','regressions':[]}
    failures=result['regressions']
    try:
        raw=(root/BASELINE).read_bytes()
        if digest(raw)!=BASELINE_SHA256: raise ValueError('immutable baseline hash mismatch')
        baseline=strict_json(raw)
        result['historical_errors']=baseline['historical_errors']
        if len(result['historical_errors'])!=653: raise ValueError('historical error inventory mismatch')
        if comparison_ref is not None:
            if not re.fullmatch('[0-9a-f]{40}',comparison_ref):
                raise ValueError('trusted comparison must be an exact Git commit SHA')
            for name in baseline['append_only_prefixes']:
                previous=subprocess.run(['git','show',comparison_ref+':'+name],cwd=root,capture_output=True)
                if previous.returncode: raise ValueError('trusted history unavailable: '+name)
                if not (root/name).read_bytes().startswith(previous.stdout):
                    failures.append('history changed relative to trusted base: '+name)
            result['comparison_ref']=comparison_ref
        for name,wanted in baseline['locked_sources'].items():
            allowed=(APPROVED_VALIDATOR_SHA256,) if name=='scripts/validate_learning.py' else (wanted,)
            if digest((root/name).read_bytes()) not in allowed:
                failures.append('locked governance/validator source changed: '+name)
        for name,proof in baseline['append_only_prefixes'].items():
            current=(root/name).read_bytes()
            if digest(current[:proof['bytes']])!=proof['sha256']:
                failures.append('historical bytes changed/truncated: '+name)
                continue
            tail=current[proof['bytes']:]
            for n,line in enumerate(tail.splitlines(),1):
                if not line.strip(): continue
                try:
                    event=strict_json(line)
                    if not isinstance(event,dict): raise ValueError('event must be an object')
                    if name.endswith('decision_ledger.jsonl'):
                        if 'confidence' in event and event['confidence'] is not None and type(event['confidence']) is not int:
                            raise ValueError('confidence must be an integer')
                        if event.get('system') is not None and event['system'] not in ('PRIME_SPARTA_FANTASY_WATCH','SPARTA_BRAIN_CONTROL_ROOM','SPARTA_LIVE_CHECK','CLAUDE_SPARTA_BRAIN'):
                            raise ValueError('non-Sparta system')
                    else:
                        required=('pulse_id','sparta_decision_id','decision_timestamp_et','decision_type','subject','recommendation','confidence','actual_user_action','outcome','outcome_grade','process_grade','pulse_usefulness_grade')
                        if any(key not in event for key in required): raise ValueError('incomplete new Pulse relationship')
                except (ValueError,TypeError):
                    failures.append(f'invalid appended event: {name} suffix line {n}')
        # Never execute a changed validator and silently trust its result.
        if not any('validator source changed: scripts/validate_learning.py' in x for x in failures):
            run=subprocess.run([sys.executable,str(root/'scripts/validate_learning.py'),str(root/'learning')],capture_output=True,text=True)
            report=run.stdout+run.stderr
            result['current_report']=report
            result['current_warnings']=[x for x in report.splitlines() if x.startswith('WARNING:')]
            if run.returncode!=0: failures.append('current learning validator failed')
            added=Counter(result['current_warnings'])-Counter(baseline['allowed_v2_warnings'])
            if added: failures.append('new or worsened historical warnings')
    except (OSError,ValueError,KeyError,TypeError) as exc:
        failures.append('baseline/source validation failed: '+str(exc))
    result['passed']=not failures
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report-dir',type=Path)
    parser.add_argument('--comparison-ref',help='Exact trusted PR-base or push-before SHA; defaults to local HEAD')
    args=parser.parse_args()
    reference=args.comparison_ref or subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    report=evaluate(comparison_ref=reference)
    full='HISTORICAL PRE-V2 LEARNING FINDINGS (not suppressed or repaired):\n'+''.join('- '+x+'\n' for x in report['historical_errors'])
    full+='\nCURRENT V2 VALIDATION:\n'+report['current_report']
    full+='\nREGRESSIONS:\n'+('\n'.join(report['regressions']) or 'none')+'\n'
    print(full,end='')
    if args.report_dir:
        args.report_dir.mkdir(parents=True,exist_ok=True)
        (args.report_dir/'learning-full-report.txt').write_text(full)
        (args.report_dir/'learning-regression.json').write_text(json.dumps(report,indent=2)+'\n')
    print('LEARNING REGRESSION GATE: '+('PASS' if report['passed'] else 'FAIL')+f" historical_findings={len(report['historical_errors'])} current_warnings={len(report['current_warnings'])}")
    return 0 if report['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
