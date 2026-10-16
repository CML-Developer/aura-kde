import contextlib
import copy
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import aura_kde_v2 as v2
from aura_kde_catalog import PLUGIN

ROOT=Path(__file__).resolve().parents[1]


def initial():
    values=dict(SteamLibraryPath='file:///Steam',WallpaperWorkShopId='123',WallpaperSource='file:///Steam/scene.json+scene')
    return dict(schema=2,activity='active',targets=[dict(containment=i+1,screen=i,plugin=PLUGIN,
        geometry=dict(x=i*1920,y=0,width=1920,height=1080),groups={
        PLUGIN:{k:dict(present=True,value=v) for k,v in values.items()},
        v2.IMAGE:{k:dict(present=False,value=None) for k in v2.SPECS[v2.IMAGE]}}) for i in range(2)])


class V2Tests(unittest.TestCase):
    def evaluate(self, script):
        response=subprocess.run(['node',str(ROOT/'tests/plasma_v2_harness.js')],
            input=json.dumps(dict(state=self.state,script=script,fail=getattr(self,'_script_should_fail',False))),
            text=True,capture_output=True,check=True)
        result=json.loads(response.stdout)
        self.state=result['state'];self.last=result
        return result['output']

    def image(self):
        return dict(type='image',project='/Aura/日本 + wallpaper.png',provider='aura-store',fingerprint=[1,2,3,4])

    def run_record(self, before, item, restore=False):
        after=v2.desired_state(before,item)
        record=dict(schema=2,before=before,after=after,selection=item,fingerprint=item.get('fingerprint'))
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'record.json';path.write_text(json.dumps(record));original=path.read_bytes()
            with patch.object(v2,'evaluate',side_effect=self.evaluate),patch.object(v2.time,'sleep'),patch.object(v2,'resolve_item',return_value=item),contextlib.redirect_stdout(io.StringIO()):
                v2.run(path,restore)
            self.assertEqual(path.read_bytes(),original)
        return after

    def test_image_apply_restore_deferred_plugin_and_absent_keys(self):
        before=initial();self.state=copy.deepcopy(before)
        after=self.run_record(before,self.image())
        self.assertEqual(self.state,after)
        self.run_record(before,self.image(),True)
        self.assertEqual(self.state,before)

    def test_image_to_video_and_restore_mixed_original_plugins(self):
        before=initial()
        before['targets'][0]['plugin']=v2.IMAGE
        before['targets'][0]['groups'][v2.IMAGE]['Image']=dict(present=True,value='file:///old.png')
        self.state=copy.deepcopy(before)
        item=dict(type='video',project='/Aura/movie.mp4',source='file:///Aura/movie.mp4+video',id='aura-video-test',provider='aura-store')
        after=self.run_record(before,item)
        self.assertEqual(self.state,after)
        self.run_record(before,item,True)
        self.assertEqual(self.state,before)

    def test_script_failure_restores_first_screen_and_absence(self):
        self.state=initial();before=copy.deepcopy(self.state);self._script_should_fail=True
        result=self.evaluate(v2.script(before,v2.desired_state(before,self.image())))
        self.assertFalse(result['ok'])
        self.assertEqual(result['rollbackErrors'],[])
        self.assertEqual(self.state,before)

    def test_conflict_does_not_write(self):
        before=initial();self.state=copy.deepcopy(before)
        self.state['targets'][1]['groups'][PLUGIN]['WallpaperWorkShopId']['value']='user-change'
        result=self.evaluate(v2.script(before,v2.desired_state(before,self.image())))
        self.assertFalse(result['ok']);self.assertEqual(self.last['writes'],[])

    def test_restore_preserves_external_change(self):
        before=initial();self.state=v2.desired_state(before,self.image())
        self.state['targets'][0]['groups'][v2.IMAGE]['Image']['value']='file:///user.png'
        saved=copy.deepcopy(self.state)
        with self.assertRaisesRegex(ValueError,'outside Aura'):self.run_record(before,self.image(),True)
        self.assertEqual(self.state,saved)

    def test_restore_after_interrupted_blank_phase(self):
        before=initial();item=dict(type='video',project='/Aura/movie.mp4',source='file:///Aura/movie.mp4+video',id='aura-video-test')
        self.state=v2.blank_state(v2.desired_state(before,item))
        self.run_record(before,item,True)
        self.assertEqual(self.state,before)

    def test_read_after_setter_is_not_activation(self):
        self.state=initial();before=copy.deepcopy(self.state)
        after=v2.desired_state(before,self.image())
        self.evaluate(v2.script(before,after))
        self.assertEqual(self.last['beforeCleanup'],[PLUGIN,PLUGIN])
        self.assertEqual([t['plugin'] for t in self.state['targets']],[v2.IMAGE,v2.IMAGE])

    def test_unknown_plugin_and_duplicate_targets_rejected(self):
        for field,value in [('plugin','org.kde.slideshow'),('screen',0)]:
            state=initial();state['targets'][1][field]=value
            with self.assertRaises(ValueError):v2.validate(state)
