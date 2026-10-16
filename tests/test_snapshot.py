import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('node'), 'Node required for isolated JavaScript contract tests')
class SnapshotScriptTests(unittest.TestCase):
    def test_filters_inactive_and_preserves_absence_and_group(self):
        harness = r'''
const fs = require('fs');
let printed;
function currentActivity() { return 'active'; }
function screenGeometry(screen) { return {x: screen * 1920, y: 0, width: 1920, height: 1080}; }
function make(id, screen) {
  return { id, screen, wallpaperPlugin: 'com.github.catsout.wallpaperEngineKde',
    currentConfigGroup: ['Original'], configKeys: ['WallpaperSource'],
    readConfig(key) { return "file:///space%20quote%27日本/scene.json+scene"; },
    writeConfig() { throw new Error('Unexpected write'); }
  };
}
const ds = [make(1, 0), make(2, 1), make(3, -1)];
function desktopsForActivity(id) { if (id !== 'active') throw new Error('Wrong activity'); return ds; }
function print(value) { printed = value; }
eval(fs.readFileSync(process.argv[1], 'utf8'));
if (ds.some(d => JSON.stringify(d.currentConfigGroup) !== '["Original"]')) throw new Error('Group was not restored');
process.stdout.write(printed);
'''
        result = subprocess.run(['node', '-e', harness, str(ROOT / 'tools/plasma_snapshot.js')],
                                text=True, capture_output=True, check=True)
        data = json.loads(result.stdout)
        self.assertEqual([t['screen'] for t in data['targets']], [0, 1])
        self.assertEqual(data['targets'][1]['geometry']['x'], 1920)
        self.assertEqual(data['targets'][0]['values']['SteamLibraryPath'], {'present': False, 'value': None})
        self.assertTrue(data['targets'][0]['values']['WallpaperSource']['present'])
