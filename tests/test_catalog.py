import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('catalog', Path(__file__).resolve().parents[1] / 'tools/aura_kde_catalog.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.library = Path(self.temp.name) / "Steam '日本 + space"
        self.folder = self.library / 'steamapps/workshop/content/431960/123'
        self.folder.mkdir(parents=True)
        self.project = self.folder / 'project.json'
        self.config = Path(self.temp.name) / 'plasma.ini'

    def project_data(self, **data):
        self.project.write_text(json.dumps(data))

    def desktops(self, screens=(0, 1)):
        self.config.write_text('\n'.join(
            f'[Containments][{i+1}]\nplugin=org.kde.plasma.folder\nactivityId=active\nlastScreen={screen}\nwallpaperplugin={m.PLUGIN}\n'
            f'[Containments][{i+1}][Wallpaper][{m.PLUGIN}][General]\nWallpaperSource[$e]=file:$HOME/old+scene\n'
            for i, screen in enumerate(screens)))

    def test_packed_scene_and_both_targets(self):
        self.project_data(type='Scene', file='scene.json', title='日本')
        (self.folder / 'scene.pkg').touch()
        self.desktops()
        result = m.plan(self.library, '123', self.config, 'active')
        self.assertEqual(len(result['targets']), 2)
        self.assertFalse(result['can_apply'])
        self.assertTrue(result['wallpaper']['usable'])
        self.assertFalse(result['targets'][0]['before']['WallpaperWorkShopId']['present'])
        self.assertEqual(result['targets'][0]['before']['WallpaperSource']['raw_entries'], {'WallpaperSource[$e]': 'file:$HOME/old+scene'})

    def test_unicode_quotes_plus_uri(self):
        name = "test '日本 +.mp4"
        self.project_data(type='Video', file=name)
        (self.folder / name).touch()
        item = m.inspect_project(self.project)
        self.assertEqual(item['source'], (self.folder / name).as_uri() + '+video')
        self.assertNotIn(' ', item['source'])
        self.assertIn('%2B', item['source'])

    def test_traversal_and_symlink_rejected(self):
        for name in ('../escape.mp4', '/tmp/escape.mp4'):
            self.project_data(type='video', file=name)
            with self.assertRaises(ValueError):
                m.inspect_project(self.project)
        (self.folder / 'escape.mp4').symlink_to('/tmp/escape.mp4')
        self.project_data(type='video', file='escape.mp4')
        with self.assertRaises(ValueError):
            m.inspect_project(self.project)

    def test_bad_json_and_unknown_type(self):
        self.project.write_text('{')
        self.assertEqual(m.catalog(self.library), [])
        self.project_data(file='anything')
        self.assertEqual(m.catalog(self.library), [])

    def test_excluded_wallpaper_preserves_reason(self):
        folder = self.folder.parent / '2888802755'
        folder.mkdir()
        project = folder / 'project.json'
        project.write_text(json.dumps(dict(type='video', file='video.mp4')))
        (folder / 'video.mp4').touch()
        item = m.inspect_project(project)
        self.assertFalse(item['usable'])
        self.assertEqual(item['reason'], 'known to crash on Linux')
        self.assertEqual(m.catalog(self.library), [])

    def test_missing_resource(self):
        self.project_data(type='web', file='index.html')
        self.assertFalse(m.inspect_project(self.project)['usable'])

    def test_ambiguous_or_wrong_activity_rejected(self):
        self.desktops((0, 0))
        with self.assertRaises(ValueError):
            m.persisted_targets(self.config, 'active')
        self.desktops()
        with self.assertRaises(ValueError):
            m.persisted_targets(self.config, 'different')

    def test_live_plan_rejects_unsafe_restoration_and_identity(self):
        self.project_data(type='scene', file='scene.json')
        (self.folder / 'scene.pkg').touch()
        snapshot = dict(schema=1, activity='active', targets=[
            dict(containment=i+1, screen=i, plugin=m.PLUGIN,
                 geometry=dict(x=i*1920, y=0, width=1920, height=1080),
                 values={k: dict(present=True, value='old') for k in m.KEYS})
            for i in range(2)])
        result = m.live_plan(self.library, '123', snapshot)
        self.assertEqual(len(result['targets']), 2)
        self.assertFalse(result['can_apply'])
        snapshot['targets'][1]['values']['WallpaperSource']['present'] = False
        with self.assertRaises(ValueError):
            m.live_plan(self.library, '123', snapshot)
        snapshot['targets'][1]['values']['WallpaperSource']['present'] = True
        snapshot['targets'][1]['screen'] = 0
        with self.assertRaises(ValueError):
            m.live_plan(self.library, '123', snapshot)


if __name__ == '__main__':
    unittest.main()
