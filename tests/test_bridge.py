import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import aura_kde_bridge as bridge

class BridgeTests(unittest.TestCase):
    def test_declared_libraries_and_safe_previews(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp); base=home/'.local/share/Steam'; second=home/'Steam 日本'
            folder=base/'steamapps/workshop/content/431960/123';folder.mkdir(parents=True)
            (base/'steamapps/libraryfolders.vdf').write_text('"libraryfolders" { "0" { "path" "'+str(base)+'" } "1" { "path" "'+str(second)+'" }}')
            (folder/'project.json').write_text(json.dumps(dict(type='scene',file='scene.json',preview='../escape.jpg',title='Test')))
            (folder/'scene.pkg').touch()
            with patch.object(bridge.Path,'home',return_value=home), patch.dict(bridge.os.environ,{},clear=True):
                self.assertEqual(bridge.libraries(),sorted([base.resolve(),second.resolve()]))
                items=bridge.items()
                self.assertEqual(len(items),1)
                self.assertTrue(items[0]['usable'])
                self.assertNotIn('preview',items[0])

    def test_guardian_blacklist_is_read_only_and_reloaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            base = home / '.local/share/Steam'
            folder = base / 'steamapps/workshop/content/431960/123'
            folder.mkdir(parents=True)
            (folder / 'project.json').write_text(json.dumps(dict(type='video', file='clip.mp4')))
            (folder / 'clip.mp4').touch()
            blacklist = home / '.config/wallpaper-engine-safe/blacklist.txt'
            with patch.object(bridge.Path, 'home', return_value=home), patch.dict(bridge.os.environ, {}, clear=True):
                self.assertEqual(len(bridge.items()), 1)
                self.assertFalse(blacklist.exists())
                blacklist.parent.mkdir(parents=True)
                content = '123\n123\ninvalid\n12\n'
                blacklist.write_text(content)
                before = blacklist.stat()
                self.assertEqual(bridge.items(), [])
                self.assertEqual(blacklist.read_text(), content)
                self.assertEqual(blacklist.stat().st_mtime_ns, before.st_mtime_ns)
                blacklist.write_text('12\n')
                self.assertEqual(len(bridge.items()), 1)
