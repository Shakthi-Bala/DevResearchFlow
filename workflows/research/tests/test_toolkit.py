"""Integration tests for destructive-overwrite risks, provenance, and review gates."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLKIT=Path(__file__).resolve().parents[1]
REPO=TOOLKIT.parents[1]
sys.path.insert(0,str(TOOLKIT/'checks'))
from records import content_hash,load_records,parse,sha256,yaml
from validate_records import history_errors,policy_errors
from check_references import reference_errors

class ToolkitTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'project with spaces'
        self.init()
    def init(self,*args,ok=True):
        result=subprocess.run([sys.executable,str(REPO/'bin/research-init'),str(self.root),*args],capture_output=True,text=True)
        if ok: self.assertEqual(result.returncode,0,result.stderr)
        return result
    def template(self,kind):
        path=next((TOOLKIT/'templates').glob(kind+'.*'))
        return parse(path.read_text(),path.suffix=='.md')
    def put(self,relative,data):
        path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(yaml.safe_dump(data,sort_keys=False));return path
    def save(self,r):
        folders={'hypothesis':'hypotheses','experiment':'experiments','review':'reviews','claim':'claims','run':'runs','task':'tasks','observation':'observations','source':'sources'}
        relative=f'research/{folders[r["kind"]]}/{r["id"]}.yaml'
        if r['kind']=='run': relative=f'runs/{r["id"]}/manifest.yaml'
        return self.put(relative,r)
    def review(self,rid,target,stage):
        r=self.template('review');r.update(id=rid,status='completed',review_type=stage,targets=[target['id']],target_versions={target['id']:content_hash(target,stage)},disposition='supported_within_scope',checks_performed=['Independent fixture check'])
        self.save(r);return r
    def errors(self):
        records,errors=load_records(self.root)
        return errors+reference_errors(self.root,records)+policy_errors(self.root,records)
    def experiment(self):
        h=self.template('hypothesis');self.save(h)
        e=self.template('experiment');e['implementation']['file']='src/model.py';e['configuration']['file']='configs/model.yaml'
        return e
    def ready_experiment(self):
        e=self.experiment();self.put('configs/model.yaml',{'width':2})
        (self.root/'src/model.py').write_text('def model(x): return x * 2\n')
        for args in [('init','-q'),('add','src','configs'),('-c','user.name=Toolkit Test','-c','user.email=toolkit@example.invalid','commit','-qm','implementation fixture')]:
            subprocess.run(['git','-C',str(self.root),*args],check=True,capture_output=True)
        e['implementation']['commit']=subprocess.check_output(['git','-C',str(self.root),'rev-parse','HEAD'],text=True).strip()
        e['configuration']['sha256']=sha256(self.root/'configs/model.yaml')
        self.review('REV-001',e,'protocol');self.review('REV-002',e,'implementation')
        e['required_reviews']={'protocol':'REV-001','implementation':'REV-002'};e['status']='implementation_reviewed';self.save(e)
        return e
    def run_record(self):
        e=self.ready_experiment();r=self.template('run');r['status']='started'
        r['code_revision']=e['implementation']['commit'];r['configuration']['sha256']=e['configuration']['sha256']
        r['started_at']='2026-10-24T12:00:00Z';r['reviews']=['REV-001','REV-002']
        r['protocol_sha256']=content_hash(e,'protocol')
        run=self.root/'runs/RUN-001';run.mkdir()
        (run/'protocol.yaml').write_text(yaml.safe_dump(e,sort_keys=False));r['protocol_snapshot']['sha256']=sha256(run/'protocol.yaml')
        (run/'config_resolved.yaml').write_bytes((self.root/'configs/model.yaml').read_bytes())
        (run/'environment.txt').write_text('Python fixture\n');r['environment']['sha256']=sha256(run/'environment.txt')
        (run/'stdout.log').write_text('partial output\n');(run/'stderr.log').write_text('')
        self.save(r);return r
    def test_initial_install_and_validation(self):
        self.assertEqual(len(list((self.root/'.claude/agents').glob('*.md'))),7)
        self.assertEqual(self.errors(),[])
        metadata=json.loads((self.root/'research/toolkit_version.json').read_text())
        self.assertTrue(metadata['toolkit_revision']);self.assertTrue(metadata['files'])
    def test_rerun_is_byte_identical(self):
        before={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.init();after={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
    def test_update_preserves_custom_agent_and_scientific_records(self):
        agent=self.root/'.claude/agents/engineer.md';agent.write_text('custom agent\n')
        brief=self.root/'research/brief.md';brief.write_text('custom brief\n')
        self.init('--update');self.assertEqual(agent.read_text(),'custom agent\n');self.assertEqual(brief.read_text(),'custom brief\n')
    def test_update_refreshes_unchanged_owned_files(self):
        agent=self.root/'.claude/agents/engineer.md';agent.write_text('old installed version\n')
        meta=self.root/'research/toolkit_version.json';data=json.loads(meta.read_text())
        data['files']['.claude/agents/engineer.md']['sha256']=sha256(agent);meta.write_text(json.dumps(data))
        self.init('--update');self.assertEqual(agent.read_bytes(),(TOOLKIT/'agents/engineer.md').read_bytes())
    def test_existing_claude_content_preserved_once(self):
        p=self.root/'CLAUDE.md';p.write_text('Existing rules\n');self.init();self.init()
        self.assertTrue(p.read_text().startswith('Existing rules\n'));self.assertEqual(p.read_text().count('research-workflow:start'),1)
    def test_symlink_escape_rejected(self):
        outside=Path(self.temp.name)/'outside';outside.mkdir()
        (self.root/'research/brief.md').unlink();(self.root/'research/brief.md').symlink_to(outside/'brief.md')
        self.assertNotEqual(self.init(ok=False).returncode,0);self.assertFalse((outside/'brief.md').exists())
    def test_duplicate_keys_rejected(self):
        self.put('research/tasks/TASK-001.yaml',self.template('task'))
        with (self.root/'research/tasks/TASK-001.yaml').open('a') as stream: stream.write('id: TASK-002\n')
        self.assertTrue(any('duplicate key' in e for e in self.errors()))
    def test_missing_and_wrong_kind_references(self):
        h=self.template('hypothesis');h['question']='SRC-999';self.save(h)
        self.assertTrue(any('missing record' in e for e in self.errors()))
        h['question']='HYP-001';self.save(h)
        self.assertTrue(any('wrong record kind' in e for e in self.errors()))
    def test_id_filename_mismatch(self):
        h=self.template('hypothesis');self.put('research/hypotheses/HYP-002.yaml',h)
        self.assertTrue(any('does not match' in e for e in self.errors()))
    def test_protocol_gate_requires_review(self):
        e=self.experiment();e['status']='protocol_reviewed';self.save(e)
        self.assertTrue(any('protocol review required' in e for e in self.errors()))
    def test_ready_experiment_passes_then_detects_stale_review(self):
        e=self.ready_experiment();self.assertEqual(self.errors(),[])
        e['prediction']='changed prediction';self.save(e)
        self.assertTrue(any('stale review' in e for e in self.errors()))
    def test_unresolved_blocker_cannot_support(self):
        self.ready_experiment();path=self.root/'research/reviews/REV-001.yaml';r=parse(path.read_text())
        r['findings']=[{'severity':'blocking','evidence':'leakage','correction':'fix split','resolved':False}];self.save(r)
        self.assertTrue(any('blocking' in e for e in self.errors()))
    def test_inconclusive_review_does_not_unlock_execution(self):
        self.ready_experiment();path=self.root/'research/reviews/REV-001.yaml';r=parse(path.read_text())
        r['disposition']='insufficient_evidence';self.save(r)
        self.assertTrue(any('protocol review required' in e for e in self.errors()))
    def test_run_retains_partial_failure_evidence(self):
        r=self.run_record();self.assertEqual(self.errors(),[])
        r.update(status='failed',finished_at='2026-10-24T12:01:00Z',exit_code=1,failure_reason='fixture failure');self.save(r)
        self.assertEqual(self.errors(),[]);self.assertTrue((self.root/'runs/RUN-001/stdout.log').exists())
    def test_run_missing_snapshot_and_bad_checksum(self):
        r=self.run_record();(self.root/'runs/RUN-001/protocol.yaml').unlink()
        self.assertTrue(any('protocol' in e for e in self.errors()))
        self.assertTrue((self.root/'runs/RUN-001/stdout.log').exists())
    def test_run_patch_must_match_implementation_review(self):
        r=self.run_record();patch=self.root/'runs/RUN-001/changes.patch';patch.write_text('unreviewed patch\n')
        r['patch']={'path':'runs/RUN-001/changes.patch','sha256':sha256(patch)};self.save(r)
        self.assertTrue(any('patch differs' in e for e in self.errors()))
    def test_run_artifact_corruption_detected(self):
        self.run_record();(self.root/'runs/RUN-001/config_resolved.yaml').write_text('changed config\n')
        self.assertTrue(any('checksum mismatch' in e for e in self.errors()))
    def test_claim_promotion_requires_evidence_review(self):
        c=self.template('claim');c['status']='provisionally_supported';self.save(c)
        self.assertTrue(any('current independent evidence review' in e for e in self.errors()))
    def test_stale_dependency_requires_claim_review(self):
        c=self.template('claim');c['dependencies']=[{'path':'src/model.py','sha256':'0'*64}]
        (self.root/'src/model.py').write_text('changed\n');self.save(c)
        self.assertTrue(any('stale dependency' in e for e in self.errors()))
        c['status']='needs_review';self.save(c);self.assertEqual(self.errors(),[])
    def test_artifact_symlink_escape_rejected(self):
        c=self.template('claim');outside=Path(self.temp.name)/'external';outside.write_text('outside')
        (self.root/'src/link').symlink_to(outside);c['dependencies']=[{'path':'src/link','sha256':sha256(outside)}];self.save(c)
        self.assertTrue(any('escapes project' in e for e in self.errors()))
    def test_history_forbids_skipping_experiment_gates(self):
        e=self.experiment();self.save(e)
        for args in [('init','-q'),('add','.'),('-c','user.name=Toolkit Test','-c','user.email=toolkit@example.invalid','commit','-qm','fixture')]:
            subprocess.run(['git','-C',str(self.root),*args],check=True,capture_output=True)
        e['status']='completed';self.save(e);records,_=load_records(self.root)
        self.assertTrue(any('forbidden transition' in e for e in history_errors(self.root,records,'HEAD')))
    def test_completed_run_cannot_be_mutated_or_deleted(self):
        r=self.run_record();r.update(status='failed',finished_at='2026-10-24T12:01:00Z',exit_code=1,failure_reason='fixture failure');self.save(r)
        for args in [('add','.'),('-c','user.name=Toolkit Test','-c','user.email=toolkit@example.invalid','commit','-qm','failed run fixture')]:
            subprocess.run(['git','-C',str(self.root),*args],check=True,capture_output=True)
        r['failure_reason']='rewritten';self.save(r);records,_=load_records(self.root)
        self.assertTrue(any('immutable' in e for e in history_errors(self.root,records,'HEAD')))
        (self.root/'runs/RUN-001/manifest.yaml').unlink();records,_=load_records(self.root)
        self.assertTrue(any('deleted' in e for e in history_errors(self.root,records,'HEAD')))
    def test_nonexistent_revision_rejected(self):
        e=self.ready_experiment();e['implementation']['commit']='0'*40
        self.review('REV-002',e,'implementation');self.save(e)
        self.assertTrue(any('commit must exist' in e for e in self.errors()))
    def test_installed_validation_cli(self):
        for script in ['validate_records.py','check_references.py']:
            result=subprocess.run([sys.executable,str(self.root/'.research-toolkit/checks'/script),str(self.root)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    def test_agent_frontmatter_and_ownership(self):
        for path in (self.root/'.claude/agents').glob('*.md'):
            data=parse(path.read_text(),True)
            self.assertEqual(data['name'],path.stem)
            self.assertTrue(data['description']);self.assertTrue(data['tools'])
            self.assertIn('Permitted writing area',path.read_text())
            if path.stem!='coordinator': self.assertNotIn('Agent',data['tools'])
    def test_every_template_satisfies_its_schema(self):
        from jsonschema import Draft202012Validator,FormatChecker
        for path in (TOOLKIT/'templates').glob('*'):
            if path.stem in {'brief','state'}: continue
            record=parse(path.read_text(),path.suffix=='.md')
            schema=json.loads((TOOLKIT/'schemas'/f'{record["kind"]}.schema.json').read_text())
            self.assertEqual(list(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(record)),[],path.name)

if __name__=='__main__': unittest.main()
