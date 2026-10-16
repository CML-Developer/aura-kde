import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import aura_kde_store as store
import aura_kde_apply as app
import aura_kde_bridge as bridge
from aura_kde_catalog import PLUGIN


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.home / 'config')})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.home_patch = patch.object(Path, 'home', return_value=self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)
        self.folder = store.download_dir()
        self.folder.mkdir(parents=True)
        self.video = self.folder / "日本 ' + clip.mp4"
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=blue:s=32x32:d=0.1',
                        '-c:v', 'mpeg4', '-y', str(self.video)], check=True, timeout=15)
        values = dict(SteamLibraryPath='file:///Steam', WallpaperWorkShopId='123', WallpaperSource='file:///Steam/scene.json+scene')
        self.before = dict(schema=1, activity='active', targets=[dict(containment=i+1, screen=i,
            plugin=PLUGIN, geometry=dict(x=i*1920,y=0,width=1920,height=1080),
            values={k:dict(present=True,value=v) for k,v in values.items()}) for i in range(2)])

    def test_catalog_and_probe_and_bridge(self):
        item = store.inspect_video(self.video, probe=True)
        self.assertTrue(item['id'].startswith('aura-video-'))
        self.assertIn('%2B', item['source'])
        self.assertTrue(item['downloaded'])
        with patch.object(bridge, 'libraries', return_value=[]):
            self.assertEqual(bridge.items(), [item])
        self.assertEqual(store.download_dir(), self.folder)

    def test_incomplete_html_external_symlink_and_no_video(self):
        (self.folder/'partial.mp4.tmp').write_bytes(b'incomplete')
        (self.folder/'error.mp4').write_text('<html>error</html>')
        outside = self.home / 'outside.mp4'
        outside.write_bytes(self.video.read_bytes())
        (self.folder/'escape.mp4').symlink_to(outside)
        self.assertEqual(len(store.items()), 1)
        with self.assertRaises(ValueError): store.inspect_video(outside)
        fake = self.folder/'fake.mp4'
        fake.write_bytes(b'\x00\x00\x00\x18ftypisom')
        with self.assertRaises(subprocess.CalledProcessError): store.inspect_video(fake, probe=True)

    def test_backup_apply_restore_both_and_changed_download(self):
        with patch.object(app, 'snapshot', return_value=self.before):
            record_path = app.prepare_video(self.video)
        self.assertEqual(record_path.stat().st_mode & 0o777, 0o600)
        original = record_path.read_bytes()
        record = json.loads(original)
        after = copy.deepcopy(self.before)
        for target in after['targets']:
            target['values'] = {k:dict(present=True,value=v) for k,v in record['proposed'].items()}
        with patch.object(app, 'snapshot', side_effect=[self.before, after, after, self.before]), patch.object(app, 'evaluate', return_value={'ok':True}) as evaluate, patch.object(app.time, 'sleep'), contextlib.redirect_stdout(io.StringIO()):
            app.run(record_path, False)
            app.run(record_path, True)
        self.assertEqual(evaluate.call_count, 4)
        payloads = [json.loads(call.args[0].splitlines()[0][14:-1]) for call in evaluate.call_args_list]
        self.assertEqual(payloads[1]['proposed'], record['proposed'])
        self.assertEqual(payloads[3]['proposed']['WallpaperWorkShopId'], '123')
        self.assertTrue(all(len(p['before']['targets']) == 2 for p in payloads))
        self.assertEqual(record_path.read_bytes(), original)
        with self.video.open('ab') as stream: stream.write(b'changed')
        with patch.object(app, 'snapshot', return_value=self.before), patch.object(app, 'evaluate') as evaluate:
            with self.assertRaisesRegex(ValueError, 'changed'): app.run(record_path, False)
            evaluate.assert_not_called()
        # Restore remains possible even if the downloaded file disappears.
        self.video.unlink()
        with patch.object(app, 'snapshot', side_effect=[after, self.before]), patch.object(app, 'evaluate', return_value={'ok':True}), patch.object(app.time, 'sleep'), contextlib.redirect_stdout(io.StringIO()):
            app.run(record_path, True)

    def test_different_libraries_rejected(self):
        self.before['targets'][1]['values']['SteamLibraryPath']['value'] = 'file:///Other'
        with self.assertRaisesRegex(ValueError, 'same Steam library'):
            store.video_plan(self.video, self.before)
