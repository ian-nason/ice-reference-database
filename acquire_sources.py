"""Fetch exactly the pinned source files; reuse only fully verified local bytes."""
from pathlib import Path
import hashlib,json,os,shutil,tempfile,urllib.request,zipfile
from build_safety import require,digest
ROOT=Path(__file__).resolve().parent
RESERVE=512*1024**2

def safe_path(root, relative):
    path=(root/relative).resolve()
    require(path.is_relative_to(root.resolve()), 'Source path escapes repository')
    return path

def verify(path,item):
    require(path.stat().st_size==item['bytes'],f'Wrong source size: {path}')
    require(digest(path)==item['sha256'],f'Wrong source SHA256: {path}')

def publish_stream(stream,path,item):
    require(0<=item['bytes']<=32*1024**2,'Individual source exceeds bounded acquisition limit')
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():verify(path,item);return
    require(shutil.disk_usage(path.parent).free>=RESERVE+item['bytes'],'Insufficient physical source-download reserve')
    fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'-',suffix='.part',dir=path.parent)
    part=Path(tmp)
    with os.fdopen(fd,'wb') as out:
        total=0
        while True:
            block=stream.read(min(1024**2,item['bytes']-total+1))
            if not block:break
            total+=len(block)
            require(total<=item['bytes'],'Source stream exceeds pinned length')
            require(shutil.disk_usage(path.parent).free>=RESERVE+len(block),'Physical download reserve crossed')
            out.write(block)
    verify(part,item)
    require(shutil.disk_usage(path.parent).free>=RESERVE,'Physical download reserve crossed')
    os.link(part,path)  # atomic no-clobber; retain private bytes on any failure
    part.unlink()      # remove only this function's completed temporary hard link

def acquire(root=ROOT):
    lock=json.loads((root/'source-lock.json').read_text())
    for item in lock['downloads']:
        path=safe_path(root,item['local_path'])
        if path.exists():verify(path,item)
        else:
            require(item['url'].startswith('https://'),'Only pinned HTTPS sources are supported')
            with urllib.request.urlopen(item['url'],timeout=60) as response:
                require(response.status==200,'Unexpected source HTTP status')
                publish_stream(response,path,item)
        if path.suffix=='.zip':
            expected={x['file']:x for x in lock['tables']}
            with zipfile.ZipFile(path) as archive:
                members=archive.infolist()
                require(len(members)==len(expected),'Unexpected archive member count')
                require({m.filename for m in members}==set(expected),'Unexpected archive paths')
                require(sum(m.file_size for m in members)<=4*1024**2,'Archive expanded size exceeds cap')
                for member in members:
                    spec=expected[member.filename]
                    require(member.file_size==spec['bytes'],'Archive member length differs from pin')
                    target=safe_path(root,spec['local_path'])
                    if target.exists():verify(target,spec)
                    else:
                        with archive.open(member) as stream:publish_stream(stream,target,spec)
    for table in lock['tables']:verify(safe_path(root,table['local_path']),table)
    return {'status':'all pinned files verified','tables':len(lock['tables'])}

if __name__=='__main__':print(json.dumps(acquire()))
