import argparse, json, os, urllib.request

def post(url, data, headers):
    req=urllib.request.Request(url,data=json.dumps(data).encode(),headers={'Content-Type':'application/json',**headers},method='POST')
    with urllib.request.urlopen(req) as r:return json.load(r)

def main():
    p=argparse.ArgumentParser(description='KAIRO trust-anchor demonstration CLI')
    p.add_argument('action',choices=['anchor']);p.add_argument('--host',default=os.environ.get('KAIRO_HOST','http://localhost:8000'));p.add_argument('--email',default='forensic@kairo.local');p.add_argument('--password',default='KairoDemo!2026');p.add_argument('--evidence-id',type=int,required=True);a=p.parse_args()
    login=post(a.host+'/api/login',{'email':a.email,'password':a.password},{})
    r=post(a.host+f'/api/trust/anchor/{a.evidence_id}',{}, {'Authorization':'Bearer '+login['access_token']})
    print(json.dumps(r,indent=2))
if __name__=='__main__':main()
