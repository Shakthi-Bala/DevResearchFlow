#!/usr/bin/env python3
"""Generate and execute a complete, explicitly synthetic workflow demonstration."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'workflows/research/checks'))
from records import content_hash, parse, sha256, yaml
from record_helper import template


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',help='new directory, outside this checkout')
    args=parser.parse_args()
    root=Path(args.destination).expanduser().resolve()
    if root.exists() or root.is_relative_to(REPO):
        parser.error('choose a new destination outside the toolkit checkout')
    root.mkdir(parents=True)

    def command(*argv,check=True):
        return subprocess.run(argv,cwd=root,capture_output=True,text=True,check=check)
    def git(*argv):
        return command('git',*argv).stdout.strip()
    def commit(message):
        git('add','.')
        # Example history is local, with an explicitly fictional identity.
        git('-c','user.name=Workflow Demo','-c','user.email=demo@example.invalid',
            '-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false','commit','-qm',message)
    def write(path,text):
        target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text)
    def record(kind,**values):
        r=template(kind);r['scope']={'project':'Synthetic teaching fixture; no independent scientific review'}
        r.update(values);return r
    def save(r):
        folders={'question':'questions','hypothesis':'hypotheses','experiment':'experiments',
                 'review':'reviews','observation':'observations','claim':'claims','decision':'decisions'}
        relative=f'research/{folders[r["kind"]]}/{r["id"]}.yaml' if r['kind']!='run' else f'runs/{r["id"]}/manifest.yaml'
        # Initial question is Markdown; retain one canonical file per ID.
        if r['kind']=='question':
            (root/'research/questions/Q-001.md').unlink(missing_ok=True)
        write(relative,yaml.safe_dump(r,sort_keys=False))
    def review(rid,stage,targets):
        r=record('review',id=rid,status='completed',review_type=stage,
                 targets=[t['id'] for t in targets],
                 target_versions={t['id']:content_hash(t,stage) for t in targets},
                 disposition='supported_within_scope',
                 checks_performed=['SYNTHETIC REVIEW FIXTURE: demonstrates schema and linking only.'],
                 not_verified=['No independent reviewer or model session was used. Not thesis evidence.'])
        save(r);return r
    def validate(ok=True):
        result=command(sys.executable,str(REPO/'workflows/research/checks/validate_records.py'),str(root),check=False)
        if ok and result.returncode:
            raise RuntimeError(result.stdout+result.stderr)
        return result
    def helper(*argv):
        return command(sys.executable,str(root/'.research-toolkit/checks/record_helper.py'),*argv)

    git('init','-q')
    command(sys.executable,str(REPO/'bin/research-init'),str(root))
    write('README.md','# Synthetic toy ablation\n\nGenerated demonstration only. Reviews are labeled fixtures, not independent judgments.\n')
    write('research/brief.md','# Demo brief\n\nTest whether removing a slope improves mean squared error on x=1,2,3,4 and y=2x.\nBudget: two tiny local executions, including an injected failure. No external data or model calls.\nThis is a teaching fixture, not a PI-approved thesis experiment.\n')
    write('src/ablation.py','''import argparse, json
p=argparse.ArgumentParser();p.add_argument('--fail',action='store_true');a=p.parse_args()
print('Evaluating deterministic synthetic points',flush=True)
if a.fail: raise SystemExit('Injected demonstration failure before metrics')
from pathlib import Path
data=json.loads(Path('configs/dataset.json').read_text());x=data['x'];y=data['y']
config=json.loads(Path('configs/ablation.json').read_text())
baseline=sum((config['baseline_slope']*v-t)**2 for v,t in zip(x,y))/len(x)
ablated=sum((config['ablated_slope']*v-t)**2 for v,t in zip(x,y))/len(x)
print(json.dumps({'baseline_mse':baseline,'ablated_mse':ablated,'difference':ablated-baseline}))
''')
    write('configs/ablation.json',json.dumps({'baseline_slope':2,'ablated_slope':1})+'\n')
    write('configs/dataset.json',json.dumps({'x':[1,2,3,4],'y':[2,4,6,8]})+'\n')
    write('configs/environment.txt',sys.version+'\n')
    q=record('question',status='active',question='Does removing the slope reduce MSE?',
             observable_outcome='Compare deterministic MSE on four synthetic points.',constraints=['Teaching fixture only'])
    h=record('hypothesis',statement='Removing the slope reduces MSE.',alternatives=['Removing it increases error.'],
             falsification_conditions=['Ablated MSE is greater than baseline MSE.'])
    e=record('experiment',hypothesis='HYP-001',prediction='Ablated MSE is lower.',baselines=['2*x'],
             controlled_variables=['Four fixed points and targets'],ablations=['Replace 2*x with x'],
             metrics=[{'name':'MSE','units':'squared target units','aggregation':'mean over all four points'}],
             data_separation='Deterministic illustration; no training or generalization claim.',
             repetitions='One deterministic calculation per successful execution; no sampling uncertainty.',
             failure_criteria=['Nonzero exit or missing JSON metrics'],budget='Two tiny CPU attempts',
             interpretation_limits=['Only these four synthetic points'],measurement_protocol={'conditions':'CPU; no stochastic components'},
             implementation={'file':'src/ablation.py','symbol':'module','commit':None,'patch':None},
             configuration={'file':'configs/ablation.json','sha256':None})
    save(q);save(h);save(e);validate();commit('Demo: define question, hypothesis and draft protocol')
    old=review('REV-001','protocol',[e]);e['required_reviews']['protocol']='REV-001';e['status']='protocol_reviewed';save(e)
    validate();commit('Demo: initial protocol review fixture')
    e.update(version=2,status='draft',prediction='Ablated MSE is strictly below baseline MSE (difference < 0).')
    save(e)
    stale=validate(False)
    if stale.returncode==0 or 'stale review' not in stale.stdout:
        raise RuntimeError('stale review demonstration did not fail as expected')
    write('research/sessions/stale-review.txt',stale.stdout)
    old['status']='superseded';save(old);review('REV-002','protocol',[e])
    e['required_reviews']['protocol']='REV-002';e['status']='protocol_reviewed';save(e)
    validate();commit('Demo: preserve stale review and replace it for protocol version 2')
    e['implementation']['commit']=git('rev-parse','HEAD')
    e['configuration']['sha256']=sha256(root/'configs/ablation.json')
    review('REV-003','implementation',[e]);e['required_reviews']['implementation']='REV-003'
    e['status']='implementation_reviewed';save(e);validate();commit('Demo: pin implementation and configuration with review fixture')
    for rid,fail in [('RUN-001',True),('RUN-002',False)]:
        helper('prepare-run',rid,'research/experiments/EXP-001.yaml','--environment','configs/environment.txt',
               '--dataset-version','synthetic-v1','--dataset-manifest','configs/dataset.json',
               '--device','CPU','--exec',sys.executable,'src/ablation.py',*(['--fail'] if fail else []))
    validate();commit('Demo: prepare two planned runs without executing')
    e['status']='executing';e['runs']=['RUN-001','RUN-002'];save(e)
    h['status']='under_test';save(h);validate();commit('Demo: begin reviewed experiment')
    for rid in ['RUN-001','RUN-002']:
        manifest=root/f'runs/{rid}/manifest.yaml';r=parse(manifest.read_text())
        write(r['logs']['stdout'],'');write(r['logs']['stderr'],'')
        r.update(status='started',started_at=datetime.now(timezone.utc).isoformat());save(r)
        validate();commit(f'Demo: start {rid}')
        result=command(*r['command'],check=False)
        write(r['logs']['stdout'],result.stdout);write(r['logs']['stderr'],result.stderr)
        r.update(status='failed' if result.returncode else 'completed',exit_code=result.returncode,
                 finished_at=datetime.now(timezone.utc).isoformat(),
                 failure_reason='Injected teaching failure; see stderr.' if result.returncode else None)
        if result.returncode==0:
            metrics=json.loads(result.stdout.splitlines()[-1]);write(f'runs/{rid}/metrics.json',json.dumps(metrics,indent=2)+'\n')
            r['metrics']={'path':f'runs/{rid}/metrics.json','sha256':sha256(root/f'runs/{rid}/metrics.json')}
        save(r);validate();commit(f'Demo: preserve {rid} actual outputs and terminal result')
    e['status']='completed';save(e)
    write('analysis/check.py',"import json\nfrom pathlib import Path\nm=json.loads(Path('runs/RUN-002/metrics.json').read_text())\ndata=json.loads(Path('configs/dataset.json').read_text())\nexpected=sum(v*v for v in data['x'])/len(data['x'])\nassert m == {'baseline_mse':0.0,'ablated_mse':expected,'difference':expected}\nprint('Recomputed expected MSE: (1+4+9+16)/4 = 7.5')\n")
    commit('Demo: finish experiment and add reproducible analysis')
    analysis=command(sys.executable,'analysis/check.py')
    write('research/sessions/analysis.txt',analysis.stdout)
    obs=record('observation',run='RUN-002',measurement='Ablated minus baseline MSE',units='squared target units',value=7.5,
               uncertainty='Exact arithmetic on these four deterministic points; no generalization estimate.',
               raw_artifacts=[r['metrics']],analysis={'file':'analysis/check.py','commit':git('rev-parse','HEAD'),
                                                     'command':[sys.executable,'analysis/check.py']})
    claim=record('claim',statement='Removing the slope increases MSE from 0 to 7.5 on the four demo points.',
                 supporting_evidence=['OBS-001'],contradicting_evidence=[],limitations=['Four fixed synthetic points only'],
                 check_methods=['numerical_check'],dependencies=[{'path':'analysis/check.py','sha256':sha256(root/'analysis/check.py')}])
    h['contradicting_evidence']=['OBS-001'];save(h);save(obs);save(claim)
    validate();commit('Demo: record measurements and scoped interpretation before evidence review')
    review('REV-004','evidence',[h,obs,claim])
    h.update(status='contradicted',review_records=['REV-004']);obs.update(status='reviewed',review_records=['REV-004'])
    claim.update(status='provisionally_supported',review_records=['REV-004']);save(h);save(obs);save(claim)
    decision=record('decision',status='accepted',action='reject',rationale='The measured difference is positive, contradicting HYP-001 within this fixture.',
                    claims=['CLM-001'],reviews=['REV-004'])
    save(decision);q['status']='resolved';save(q)
    write('research/state.yaml',yaml.safe_dump({'phase':'complete','active_question':'Q-001','active_tasks':[],
          'current_experiment':'EXP-001','blockers':[],'next_decision':'Replace fixture reviews with independent review for real research.'},sort_keys=False))
    validate();commit('Demo: record fixture evidence review, contradicted hypothesis and decision')
    # Every recorded transition must also pass against its immediate parent.
    for revision in git('rev-list','--reverse','HEAD').splitlines():
        command(sys.executable,str(REPO/'workflows/research/checks/validate_snapshot.py'),str(root),'--commit',revision)
    print(f'Example created: {root}\nActual MSE: baseline 0, ablated 7.5. One failed run retained.\nAll commit snapshots validated. Reviews are synthetic fixtures, not independent judgments.')

if __name__=='__main__':
    main()
