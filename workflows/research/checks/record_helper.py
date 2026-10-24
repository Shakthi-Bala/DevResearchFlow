#!/usr/bin/env python3
"""Create draft records and capture provenance without granting review approval."""
import argparse
import re
import subprocess
from pathlib import Path
from records import FOLDERS, content_hash, local_path, parse, schema_errors, sha256, yaml

PREFIXES = dict(zip(['question','task','source','hypothesis','experiment','observation','claim','review','decision','run'],
                    ['Q','TASK','SRC','HYP','EXP','OBS','CLM','REV','DEC','RUN']))

def read(path):
    return parse(path.read_text(), path.suffix == '.md')

def output(root, relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('output must be relative to the project')
    dest = root/path
    for part in [dest, *dest.parents]:
        if part == root:
            break
        if part.is_symlink():
            raise ValueError(f'refusing symlinked output: {relative}')
    return dest

def save(path, record, markdown=False):
    errors = schema_errors(record, record['kind'])
    if errors:
        raise ValueError('; '.join(errors))
    if record['kind'] != 'run' and any(path.with_suffix(ext).exists() for ext in ('.md','.yaml','.yml','.json')):
        raise ValueError('record ID already exists; use a fresh ID')
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation: never rewrite a reviewed record or terminal manifest.
    with path.open('x') as stream:
        data = yaml.safe_dump(record, sort_keys=False)
        stream.write('---\n'+data+'---\n' if markdown else data)
    print(path)

def template(kind):
    path = next((Path(__file__).resolve().parent.parent/'templates').glob(kind+'.*'))
    return read(path)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', default='.')
    commands = parser.add_subparsers(dest='command', required=True)
    new = commands.add_parser('new', help='create a draft from a template; fill SET_ME fields yourself')
    new.add_argument('kind', choices=PREFIXES)
    new.add_argument('id')
    review = commands.add_parser('review', help='create a pending review with current target hashes')
    review.add_argument('id')
    review.add_argument('--type', required=True, choices=['protocol','implementation','source','evidence'])
    review.add_argument('targets', nargs='+', help='project-relative record paths')
    pin = commands.add_parser('pin', help='print implementation/configuration fields for a draft experiment')
    pin.add_argument('experiment')
    run = commands.add_parser('prepare-run', help='capture a planned run and frozen provenance; does not execute')
    run.add_argument('id')
    run.add_argument('experiment')
    run.add_argument('--environment', required=True, help='existing project-relative environment capture')
    run.add_argument('--seed', type=int)
    run.add_argument('--dataset-version', required=True)
    run.add_argument('--dataset-manifest', required=True)
    run.add_argument('--device', required=True)
    run.add_argument('--exec', dest='argv', nargs=argparse.REMAINDER, required=True)
    artifact = commands.add_parser('artifact', help='print a path/checksum mapping without changing records')
    artifact.add_argument('path')
    args = parser.parse_args()
    root = Path(args.project).expanduser().resolve()
    if args.command == 'artifact':
        path = local_path(root, args.path)
        print(yaml.safe_dump({'path':args.path,'sha256':sha256(path)}, sort_keys=False), end='')
        return
    if args.command == 'pin':
        record = read(local_path(root, args.experiment))
        if record.get('kind') != 'experiment' or record.get('status') != 'draft':
            raise ValueError('pin a draft experiment, then obtain fresh reviews')
        local_path(root,record['implementation']['file'])
        commit = subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'], text=True).strip()
        changes = subprocess.check_output(['git','-C',str(root),'status','--porcelain','--',
                    record['implementation']['file'],record['configuration']['file']], text=True)
        if changes:
            raise ValueError('commit implementation and configuration before pinning')
        implementation = {**record['implementation'], 'commit':commit}
        print(yaml.safe_dump({'implementation':implementation,
              'configuration':{**record['configuration'],'sha256':sha256(local_path(root,record['configuration']['file']))}},
              sort_keys=False), end='')
        return
    if args.command == 'new':
        record = template(args.kind)
        record['id'] = args.id
        folder = {v:k for k,v in FOLDERS.items()}.get(args.kind)
        relative = f'research/{folder}/{args.id}.yaml' if folder else f'runs/{args.id}/manifest.yaml'
        save(output(root,relative),record)
        return
    if args.command == 'review':
        record = template('review')
        record.update(id=args.id, review_type=args.type, targets=[], target_versions={})
        allowed = {'protocol':{'experiment'},'implementation':{'experiment'},
                   'source':{'source','claim'},'evidence':{'claim','observation','hypothesis'}}
        for name in args.targets:
            target = read(local_path(root,name))
            if target.get('kind') not in allowed[args.type]:
                raise ValueError('wrong target kind for this review type')
            if schema_errors(target,target['kind']):
                raise ValueError(f'invalid target: {name}')
            record['targets'].append(target['id'])
            record['target_versions'][target['id']] = content_hash(target,args.type)
        save(output(root,f'research/reviews/{args.id}.yaml'),record)
        return
    # Check existing records before reserving a new run directory.
    from validate_records import policy_errors
    from check_references import reference_errors
    from records import load_records
    records, errors = load_records(root)
    errors += reference_errors(root,records) + policy_errors(root,records)
    if errors:
        raise ValueError('repair project validation first: '+'; '.join(errors))
    experiment = read(local_path(root,args.experiment))
    if experiment.get('kind') != 'experiment' or experiment.get('status') != 'implementation_reviewed':
        raise ValueError('prepare-run requires an implementation_reviewed experiment')
    if not re.fullmatch(r'RUN-[0-9]{3,}', args.id) or not args.argv:
        raise ValueError('provide RUN-NNN and a nonempty --exec command')
    config = local_path(root,experiment['configuration']['file']).read_bytes()
    environment = local_path(root,args.environment).read_bytes()
    dataset_hash = sha256(local_path(root,args.dataset_manifest))
    record = template('run')
    prefix = f'runs/{args.id}'
    record.update(id=args.id, scope=experiment['scope'], experiment=experiment['id'],
                  protocol_version=experiment['version'],protocol_sha256=content_hash(experiment,'protocol'),
                  code_revision=experiment['implementation']['commit'],patch=experiment['implementation']['patch'],
                  command=args.argv,seed=args.seed,hardware={'device':args.device},
                  dataset={'version':args.dataset_version,'manifest_sha256':dataset_hash},
                  reviews=list(experiment['required_reviews'].values()))
    dest = output(root,prefix)
    if dest.exists():
        raise ValueError('run directory already exists; choose a fresh run ID')
    dest.mkdir(parents=True)
    (dest/'protocol.yaml').write_text(yaml.safe_dump(experiment,sort_keys=False))
    (dest/'config_resolved.yaml').write_bytes(config)
    (dest/'environment.txt').write_bytes(environment)
    for field,name in [('protocol_snapshot','protocol.yaml'),('configuration','config_resolved.yaml'),('environment','environment.txt')]:
        record[field] = {'path':f'{prefix}/{name}','sha256':sha256(dest/name)}
    record['logs'] = {name:f'{prefix}/{name}.log' for name in ('stdout','stderr')}
    save(dest/'manifest.yaml',record)
    print('Planned only. Record actual timestamps, logs, exit code, artifacts and deviations when executing.')

if __name__ == '__main__':
    try:
        main()
    except (OSError,ValueError,KeyError,StopIteration,subprocess.CalledProcessError) as exc:
        raise SystemExit(f'record-helper: {exc}')
