"""Import a verified static Site snapshot into this GitHub Pages repository."""
import argparse
import concurrent.futures
import hashlib
import json
import shutil
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / '.migration/site-manifest.json').read_text())
parser = argparse.ArgumentParser()
parser.add_argument('--local-source', type=Path)
args = parser.parse_args()
output = ROOT / '_site'
output.mkdir(exist_ok=True)
marker = ROOT / '.migration/completed.json'
already_imported = marker.exists() and json.loads(marker.read_text()).get('source_commit') == manifest['source_commit']
text_extensions = {'.html', '.css', '.js', '.json', '.xml', '.txt'}

def transfer(entry):
    relative = Path(entry['path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    destination = output / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if args.local_source:
        data = (args.local_source / relative).read_bytes()
    elif (ROOT / relative).is_file() and hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == entry['sha256']:
        # Some hosts reserve routes such as /404.html; seed their exact files.
        data = (ROOT / relative).read_bytes()
    elif already_imported:
        data = (ROOT / relative).read_bytes()
        destination.write_bytes(data)
        return
    else:
        route = entry['path']
        if route.endswith('index.html'):
            route = route[:-len('index.html')]
        url = manifest['source_origin'] + '/' + urllib.parse.quote(route, safe='/')
        for attempt in range(5):
            try:
                request = urllib.request.Request(url, headers={'User-Agent': 'PersonalSiteMigration/1.0'})
                with urllib.request.urlopen(request, timeout=90) as response:
                    data = response.read()
                assert len(data) == entry['size'], f"Unexpected length for {relative}"
                assert hashlib.sha256(data).hexdigest() == entry['sha256'], f"Snapshot mismatch for {relative}"
                break
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(2 ** attempt)
    assert hashlib.sha256(data).hexdigest() == entry['sha256'], relative
    if relative.suffix in text_extensions:
        data = data.decode('utf-8').replace(manifest['source_origin'], manifest['target_origin']).encode('utf-8')
    destination.write_bytes(data)

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    for count, _ in enumerate(pool.map(transfer, manifest['files']), 1):
        if count % 50 == 0:
            print(f"Verified {count}/{len(manifest['files'])} files", flush=True)
(output / '.nojekyll').write_text('')

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []
        self.visible_chinese = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        for key in ['src', 'href', 'poster']:
            if key in attrs:
                self.links.append(attrs[key])
        if tag in ['script', 'style']:
            self.skip += 1
    def handle_endtag(self, tag):
        if tag in ['script', 'style']:
            self.skip -= 1
    def handle_data(self, data):
        if not self.skip and data.strip() not in ['中文', '王建明'] and any('\u3400' <= c <= '\u9fff' for c in data):
            self.visible_chinese.append(data)

pages = list(output.rglob('*.html'))
assert len(list((output / 'articles').glob('*/index.html'))) == 65
assert len(list((output / 'en/articles').glob('*/index.html'))) == 65
checks = 0
for file in pages:
    page = Page()
    text = file.read_text()
    page.feed(text)
    assert manifest['source_origin'] not in text, file
    if file.is_relative_to(output / 'en'):
        assert not page.visible_chinese, (file, page.visible_chinese)
    for link in page.links:
        if link.startswith('/'):
            target = output / urllib.parse.urlsplit(link).path.lstrip('/')
            assert target.exists(), (file, link)
        elif link.startswith('#'):
            assert link[1:] in page.ids, (file, link)
        checks += 1
print(f"PASS: {len(pages)} pages, 130 bilingual articles, {checks} link/asset references", flush=True)
for entry in manifest['files']:
    relative = Path(entry['path'])
    target = ROOT / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(output / relative, target)
(ROOT / '.nojekyll').write_text('')
marker.write_text(json.dumps({'source_commit': manifest['source_commit'], 'files': len(manifest['files']), 'article_pages': 130, 'origin': manifest['target_origin']}, indent=2) + '\n')
