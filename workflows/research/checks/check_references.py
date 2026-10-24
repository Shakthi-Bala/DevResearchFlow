#!/usr/bin/env python3
"""Validate record references and local artifact checksums, not scientific correctness."""
import argparse
import re
from pathlib import Path
from records import content_hash,load_records,local_path,sha256
ID = re.compile(r'^(Q|TASK|SRC|HYP|EXP|RUN|OBS|CLM|REV|DEC)-[0-9]{3,}$')
LINKS = {'references','supersedes','question','hypothesis','planned_tests','supporting_evidence',
         'contradicting_evidence','review_records','dependencies','outputs','runs','experiment',
         'run','reviews','targets','claims','protocol','implementation','reference'}
EXPECTED = {'question':{'question'},'hypothesis':{'hypothesis'},'planned_tests':{'experiment'},
            'review_records':{'review'},'runs':{'run'},'experiment':{'experiment'},'run':{'run'},
            'reviews':{'review'},'claims':{'claim'},'protocol':{'review'},'implementation':{'review'}}

def reference_errors(root,records):
    errors = []
    for rid,(record,path) in records.items():
        def report(message): errors.append(f'{rid}: {message}')
        pending_run=(record['kind']=='run' and
                     (record['status']=='planned' or (record['status']=='cancelled' and record['started_at'] is None)))
        def walk(value,field='',active=False):
            if isinstance(value,dict):
                if 'path' in value and 'sha256' in value and not pending_run:
                    try:
                        file=local_path(root,value['path'])
                        if sha256(file)!=value['sha256'] and not (record['kind']=='claim' and record['status'] in {'needs_review','superseded'}):
                            report(f'checksum mismatch / stale dependency: {value["path"]}')
                    except (ValueError,OSError) as exc:
                        retained_stale=(record['kind']=='claim' and record['status'] in {'needs_review','superseded'} and str(exc).startswith('missing file:'))
                        if not retained_stale: report(str(exc))
                for key,item in value.items():
                    is_link=key in LINKS and not (record['kind']=='question' and key=='question')
                    walk(item,key,is_link)
            elif isinstance(value,list):
                for item in value: walk(item,field,active)
            elif active and isinstance(value,str):
                if not ID.fullmatch(value): report(f'{field}: invalid reference {value!r}')
                elif value not in records: report(f'{field}: missing record {value}')
                elif field in EXPECTED and records[value][0]['kind'] not in EXPECTED[field]:
                    report(f'{field}: wrong record kind for {value}')
        walk(record)
        if record['kind']=='task':
            for dependency in record['dependencies']:
                if dependency in records and records[dependency][0]['kind']!='task':
                    report(f'dependencies: wrong record kind for {dependency}')
        if record['kind']=='review':
            kinds={'protocol':{'experiment'},'implementation':{'experiment'},
                   'source':{'source','claim'},'evidence':{'claim','observation','hypothesis'}}
            for target in record['targets']:
                if target in records and records[target][0]['kind'] not in kinds[record['review_type']]:
                    report(f'{record["review_type"]} review has wrong target kind: {target}')
            if set(record['target_versions'])!=set(record['targets']):
                report('target_versions must hash exactly the review targets')
            for target,digest in record['target_versions'].items():
                if target not in records: report(f'missing review target {target}')
                elif content_hash(records[target][0],record['review_type'])!=digest and record['status']!='superseded':
                    report(f'stale review target {target}; supersede this review and obtain a new review')
        if record['kind']=='run' and not pending_run:
            for value in record['logs'].values():
                try: local_path(root,value)
                except ValueError as exc: report(str(exc))
        if record['kind']=='experiment' and record['status'] not in {'draft','protocol_reviewed','superseded'}:
            locations=[record['implementation']['file'],record['configuration']['file']]
        elif record['kind']=='observation' and record['status']!='superseded': locations=[record['analysis']['file']]
        else: locations=[]
        for location in locations:
            try: local_path(root,location)
            except ValueError as exc: report(str(exc))
    visiting,visited=set(),set()
    def visit(task_id):
        if task_id in visiting:
            errors.append(f'{task_id}: cyclic task dependency')
            return
        if task_id in visited: return
        visiting.add(task_id)
        for dependency in records[task_id][0]['dependencies']:
            if dependency in records and records[dependency][0]['kind']=='task': visit(dependency)
        visiting.remove(task_id);visited.add(task_id)
    for task_id,(record,_) in records.items():
        if record['kind']=='task': visit(task_id)
    return errors

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project',nargs='?',default='.')
    root=Path(parser.parse_args().project).resolve()
    records,errors=load_records(root)
    errors.extend(reference_errors(root,records))
    for error in errors: print(error)
    print(f'{len(records)} records; {len(errors)} structural/reference errors. Scientific support is not assessed.')
    return bool(errors)
if __name__=='__main__': raise SystemExit(main())
