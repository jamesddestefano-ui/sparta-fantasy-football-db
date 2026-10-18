"""Sanitized Actions preflight. Neither secret values nor quota evidence are output."""
import json
import os
from pathlib import Path


def preflight(key,budget,evidence,rotated):
    try: confirmed=int(budget)==3
    except (ValueError,TypeError): confirmed=False
    present=bool(key.strip())
    permitted=present and confirmed and bool(evidence.strip()) and rotated is True
    return {'secret_available':present,'quota_confirmed':confirmed and bool(evidence.strip()),
            'credential_rotation_attested':rotated is True,'live_permitted':permitted,
            'status':'LIVE_PERMITTED' if permitted else 'BLOCKED_NO_API_REQUESTS',
            'api_requests':0,'season':2026,'week':6}


def main():
    result=preflight(os.environ.get('FANTASYPROS_API_KEY',''),os.environ.get('CONFIRMED_REQUEST_BUDGET','0'),
                     os.environ.get('QUOTA_EVIDENCE',''),os.environ.get('CREDENTIAL_ROTATED','false')=='true')
    Path(os.environ['PREFLIGHT_SUMMARY']).write_text(json.dumps(result,indent=2)+'\n')
    with open(os.environ['GITHUB_OUTPUT'],'a') as out:
        out.write('live_permitted='+str(result['live_permitted']).lower()+'\n')
    print(json.dumps(result))
    return 0

if __name__=='__main__': raise SystemExit(main())
