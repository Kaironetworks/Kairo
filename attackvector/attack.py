import argparse, json, os, sys, urllib.request

def main():
    p=argparse.ArgumentParser(description='KAIRO Security Lab — controlled storage tamper simulator')
    p.add_argument('action',choices=['tamper','health'])
    p.add_argument('--evidence-id',type=int)
    p.add_argument('--version',type=int,default=1)
    p.add_argument('--host',default=os.environ.get('KAIRO_HOST','http://localhost:8000'))
    args=p.parse_args()
    if args.action=='health':
        print('KAIRO SECURITY LAB\nTarget:',args.host); return
    if not args.evidence_id: p.error('--evidence-id is required')
    payload=json.dumps({'evidence_id':args.evidence_id,'version':args.version}).encode()
    req=urllib.request.Request(args.host+'/api/attack/tamper',data=payload,headers={'Content-Type':'application/json','X-Kairo-Lab-Key':os.environ.get('KAIRO_ATTACK_KEY','KAIRO-LAB-2026')},method='POST')
    try:
        with urllib.request.urlopen(req) as r: print(json.dumps(json.load(r),indent=2))
    except Exception as e:
        print('Security Lab error:',e); sys.exit(1)
if __name__=='__main__': main()
