#!/usr/bin/env python3
"""Validate an isolated Git index or commit, including history against its parent."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
from records import load_records
from check_references import reference_errors
from validate_records import history_errors, policy_errors


def git(root, *args):
    return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE)


def validate(root, staged=False, commit=None):
    top = Path(os.fsdecode(git(root,'rev-parse','--show-toplevel')).strip()).resolve()
    if root != top:
        raise ValueError('snapshot validation requires the Git repository root')
    if staged:
        entries = git(root,'ls-files','--stage','-z').split(b'\0')
        try:
            base = git(root,'rev-parse','--verify','HEAD').decode().strip()
        except subprocess.CalledProcessError:
            base = None
    else:
        commit = git(root,'rev-parse','--verify','--end-of-options',f'{commit}^{{commit}}').decode().strip()
        entries = git(root,'ls-tree','-rz',commit).split(b'\0')
        parents = git(root,'rev-list','--parents','-n','1',commit).decode().split()
        base = parents[1] if len(parents)>1 else None
    with tempfile.TemporaryDirectory(prefix='research-snapshot-') as directory:
        snapshot = Path(directory).resolve()
        for entry in entries:
            if not entry:
                continue
            metadata, name = entry.split(b'\t',1)
            mode, oid, stage = metadata.split(b' ') if staged else (metadata.split(b' ')[0],metadata.split(b' ')[2],b'0')
            if stage != b'0':
                raise ValueError('resolve Git index conflicts before validation')
            # Never traverse exported symlinks or omit submodule evidence silently.
            if mode not in {b'100644',b'100755'}:
                raise ValueError(f'snapshot contains unsupported symlink/submodule: {os.fsdecode(name)}')
            relative = Path(os.fsdecode(name))
            if relative.is_absolute() or '..' in relative.parts or '.git' in relative.parts:
                raise ValueError('unsafe path in Git snapshot')
            target = snapshot/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(git(root,'cat-file','blob',oid.decode()))
            if mode == b'100755':
                target.chmod(0o755)
        # Provenance and history need the source objects, but validation writes
        # only to this temporary repository, never to the user's index/worktree.
        object_format = git(root,'rev-parse','--show-object-format').decode().strip()
        subprocess.run(['git','init','-q',f'--object-format={object_format}',str(snapshot)],check=True)
        objects = Path(os.fsdecode(git(root,'rev-parse','--git-path','objects')).strip())
        if not objects.is_absolute():
            objects = root/objects
        alternates = snapshot/'.git/objects/info/alternates'
        alternates.write_text(str(objects.resolve())+'\n')
        if base:
            subprocess.run(['git','-C',str(snapshot),'update-ref','HEAD',base],check=True)
        records, errors = load_records(snapshot)
        errors += reference_errors(snapshot,records) + policy_errors(snapshot,records)
        if base:
            errors += history_errors(snapshot,records,base)
        for error in errors:
            print(error)
        print(f'{len(records)} records; {len(errors)} snapshot errors. Scientific support is not assessed.')
        return bool(errors)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project',nargs='?',default='.')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--staged',action='store_true')
    mode.add_argument('--commit')
    args = parser.parse_args()
    return validate(Path(args.project).resolve(),args.staged,args.commit)

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError,ValueError,subprocess.CalledProcessError) as exc:
        raise SystemExit(f'snapshot validation: {exc}')
