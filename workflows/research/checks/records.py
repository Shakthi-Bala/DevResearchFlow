"""Shared strict loading and provenance helpers; no scientific inference."""
import hashlib
import json
from pathlib import Path
try:
    import yaml
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as exc:
    raise SystemExit('Install .research-toolkit/requirements.txt (or workflows/research/requirements.txt) in a virtual environment.') from exc

class RecordLoader(yaml.SafeLoader):
    pass
RecordLoader.yaml_implicit_resolvers = {
    k: [(tag, regex) for tag, regex in entries if tag != 'tag:yaml.org,2002:timestamp']
    for k, entries in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
def mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, (str, int, float, bool, type(None))):
            raise ValueError('record keys must be scalar')
        if key in result:
            raise ValueError(f'duplicate key: {key}')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result
RecordLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
FOLDERS = {'questions':'question','tasks':'task','sources':'source','hypotheses':'hypothesis',
           'experiments':'experiment','observations':'observation','claims':'claim',
           'reviews':'review','decisions':'decision'}

def parse(text, markdown=False):
    if markdown:
        lines = text.splitlines()
        if not lines or lines[0] != '---':
            raise ValueError('Markdown record requires YAML frontmatter')
        try:
            end = lines.index('---', 1)
        except ValueError as exc:
            raise ValueError('frontmatter has no closing ---') from exc
        text = '\n'.join(lines[1:end])
    value = yaml.load(text, Loader=RecordLoader)
    if not isinstance(value, dict):
        raise ValueError('record must be a mapping')
    return value

def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            digest.update(chunk)
    return digest.hexdigest()

def content_hash(record, review_type='evidence'):
    # Exclude bookkeeping to avoid circular review/target hashes.
    data = {k:v for k,v in record.items() if k not in {
        'status','references','required_reviews','review_records','reviews','runs'}}
    if review_type == 'protocol' and record.get('kind') == 'experiment':
        data['implementation'] = {k:v for k,v in data['implementation'].items() if k not in {'commit','patch'}}
        data['configuration'] = {k:v for k,v in data['configuration'].items() if k != 'sha256'}
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',', ':'),allow_nan=False).encode()).hexdigest()

def local_path(root, value):
    path = Path(value)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError(f'artifact path must be relative to the project: {value}')
    target = (root/path).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f'artifact escapes project through a symlink: {value}')
    if not target.is_file():
        raise ValueError(f'missing file: {value}')
    return target

def load_records(root):
    records, errors, candidates = {}, [], []
    schemas = Path(__file__).resolve().parent.parent/'schemas'
    for folder, kind in FOLDERS.items():
        for path in sorted((root/'research'/folder).glob('*')):
            if path.suffix in {'.md','.yaml','.yml','.json'} and path.name != 'README.md':
                candidates.append((path,kind,path.stem))
    candidates.extend((p,'run',p.parent.name) for p in sorted((root/'runs').glob('RUN-*/manifest.yaml')))
    for path,kind,expected_id in candidates:
        label = str(path.relative_to(root))
        try:
            record = parse(path.read_text(),path.suffix == '.md')
            schema = json.loads((schemas/f'{kind}.schema.json').read_text())
            findings = sorted(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(record),key=lambda e:str(list(e.path)))
            if findings:
                errors.extend(f'{label}: {".".join(map(str,e.path)) or "record"}: {e.message}' for e in findings)
                continue
            json.dumps(record,allow_nan=False)
            if record['id'] != expected_id:
                raise ValueError(f'ID {record["id"]} does not match filename/run directory {expected_id}')
            if record['id'] in records:
                raise ValueError(f'duplicate ID: {record["id"]}')
            records[record['id']] = (record,path)
        except (ValueError,TypeError,OSError,yaml.YAMLError) as exc:
            errors.append(f'{label}: {exc}')
    if not (root/'research').is_dir():
        errors.append('missing research/ directory; run research-init first')
    for path in (root/'runs').glob('RUN-*'):
        if path.is_dir() and not (path/'manifest.yaml').is_file():
            errors.append(f'{path.name}: missing manifest.yaml; preserve raw evidence and repair manifest')
    return records,errors
