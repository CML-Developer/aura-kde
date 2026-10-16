import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from aura_kde_apply import transaction_script, restore_value
from aura_kde_catalog import KEYS, PLUGIN


@unittest.skipUnless(shutil.which('node'), 'Node required for isolated script tests')
class TransactionTests(unittest.TestCase):
    def simulate(self, mode='apply', conflict=False, fail=False, geometry=False, raw_home=False):
        before = dict(schema=1, activity='active', targets=[
            dict(containment=i+1, screen=i, plugin=PLUGIN,
                 geometry=dict(x=i*1920, y=0, width=1920, height=1080),
                 values={k: dict(present=True, value='old ' + k) for k in KEYS}) for i in range(2)])
        record = dict(schema=1, before=before, proposed={k: "new '日本 + \"\\ path" + k for k in KEYS})
        if raw_home:
            for t in before['targets']:
                t['values']['SteamLibraryPath']['value'] = 'file:$HOME/.local/share/Steam'
                t['values']['WallpaperSource']['value'] = 'file:$HOME/fondo 日本/scene.json+scene'
        script = transaction_script(record, mode == 'restore')
        harness = '''
const record = RECORD;
const writes = []; let output; let failed = false;
const ds = record.before.targets.map(t => ({
 id: t.containment, screen: t.screen, wallpaperPlugin: t.plugin,
 currentConfigGroup: ['Original'], configKeys: Object.keys(t.values),
 values: Object.fromEntries(Object.entries(t.values).map(([k,v]) => [k, RESTORE ? record.proposed[k] : v.value])),
 readConfig(k) { return this.values[k]; },
 writeConfig(k,v) {
  if (FAIL && this.id === 2 && !failed) { failed = true; throw Error('injected failure'); }
  writes.push([this.id,k,v]); this.values[k]=v;
 }
}));
if (CONFLICT) ds[1].values.WallpaperSource = 'changed by user';
function currentActivity() {return 'active';}
function desktopsForActivity(a) {return ds;}
function screenGeometry(screen) {return {x: screen*1920+(GEOMETRY ? 1 : 0),y:0,width:1920,height:1080};}
function print(x) {output=JSON.parse(x);}
SCRIPT
process.stdout.write(JSON.stringify({output,writes,values:ds.map(d=>d.values),groups:ds.map(d=>d.currentConfigGroup)}));
'''.replace('RECORD', json.dumps(record)).replace('RESTORE', str(mode == 'restore' and not raw_home).lower()).replace('CONFLICT', str(conflict).lower()).replace('FAIL', str(fail).lower()).replace('GEOMETRY', str(geometry).lower()).replace('SCRIPT', script)
        proc = subprocess.run(['node', '-e', harness], text=True, capture_output=True, check=True)
        result = json.loads(proc.stdout)
        self.assertEqual(result['groups'], [['Original'], ['Original']] if not geometry else [['Original'], ['Original']])
        return record, result

    def test_apply_both_and_escape(self):
        record, result = self.simulate()
        self.assertTrue(result['output']['ok'])
        self.assertEqual(result['values'], [record['proposed'], record['proposed']])

    def test_restore_both(self):
        record, result = self.simulate(mode='restore')
        self.assertTrue(result['output']['ok'])
        self.assertEqual(result['values'][0], {k: 'old ' + k for k in KEYS})

    def test_conflict_no_writes(self):
        for mode in ('apply', 'restore'):
            _, result = self.simulate(mode=mode, conflict=True)
            self.assertFalse(result['output']['ok'])
            self.assertEqual(result['writes'], [])
            self.assertEqual(result['values'][1]['WallpaperSource'], 'changed by user')

    def test_partial_failure_rolls_back_first_screen(self):
        _, result = self.simulate(fail=True)
        self.assertFalse(result['output']['ok'])
        self.assertEqual(result['output']['rollbackErrors'], [])
        self.assertEqual(result['values'], [{k: 'old ' + k for k in KEYS}] * 2)

    def test_geometry_change_no_writes(self):
        _, result = self.simulate(geometry=True)
        self.assertFalse(result['output']['ok'])
        self.assertEqual(result['writes'], [])

    def test_recover_already_restored_literal_home(self):
        record, result = self.simulate(mode='restore', raw_home=True)
        self.assertTrue(result['output']['ok'])
        expected = {k: restore_value(k, record['before']['targets'][0]['values'][k]['value']) for k in KEYS}
        self.assertEqual(result['values'], [expected, expected])
        self.assertNotIn('$HOME', result['values'][0]['WallpaperSource'])
        self.assertTrue(result['values'][0]['WallpaperSource'].endswith('/scene.json+scene'))

    def test_home_rollback_uses_usable_uri(self):
        record, result = self.simulate(fail=True, raw_home=True)
        self.assertFalse(result['output']['ok'])
        self.assertEqual(result['output']['rollbackErrors'], [])
        self.assertEqual(result['values'][0]['WallpaperSource'], restore_value('WallpaperSource', record['before']['targets'][0]['values']['WallpaperSource']['value']))

    def test_normalization_does_not_expand_other_variables(self):
        self.assertEqual(restore_value('SteamLibraryPath', 'file:$OTHER/path'), 'file:$OTHER/path')
        self.assertEqual(restore_value('WallpaperWorkShopId', '$HOME'), '$HOME')
        uri = (Path.home() / 'space + 日本').as_uri()
        self.assertEqual(restore_value('SteamLibraryPath', 'file:${HOME}/space + 日本'), uri)
        self.assertEqual(restore_value('SteamLibraryPath', uri), uri)
