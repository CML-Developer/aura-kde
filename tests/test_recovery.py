import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import aura_kde_apply as app
from aura_kde_catalog import KEYS, PLUGIN

class RecoveryTests(unittest.TestCase):
    def test_recovery_unloads_then_restores_without_changing_record(self):
        values = dict(SteamLibraryPath='file:///home/example/Steam', WallpaperWorkShopId='123', WallpaperSource='file:///home/example/scene.json+scene')
        before = dict(schema=1, activity='active', targets=[dict(containment=i+1, screen=i, plugin=PLUGIN, geometry=dict(x=i*1920,y=0,width=1920,height=1080), values={k:dict(present=True,value=v) for k,v in values.items()}) for i in range(2)])
        record = dict(schema=1,before=before,proposed=values)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'record.json'; path.write_text(json.dumps(record)); original=path.read_bytes()
            with patch.object(app,'snapshot',return_value=before), patch.object(app,'evaluate',return_value={'ok':True}) as evaluate, patch.object(app.time,'sleep'), contextlib.redirect_stdout(io.StringIO()):
                app.run(path,True)
            self.assertEqual(evaluate.call_count,2)
            first=json.loads(evaluate.call_args_list[0].args[0].splitlines()[0][14:-1])
            second=json.loads(evaluate.call_args_list[1].args[0].splitlines()[0][14:-1])
            self.assertEqual(first['proposed']['WallpaperSource'],'')
            self.assertFalse(first['restore'])
            self.assertFalse(second['restore'])
            self.assertEqual(second['proposed'],values)
            self.assertEqual(path.read_bytes(),original)

    def test_apply_uses_two_phases_and_original_backup(self):
        values = dict(SteamLibraryPath='file:///home/example/Steam', WallpaperWorkShopId='123', WallpaperSource='file:///home/example/scene.json+scene')
        new = dict(values,WallpaperWorkShopId='456',WallpaperSource='file:///home/example/movie.mp4+video')
        before = dict(schema=1,activity='active',targets=[dict(containment=i+1,screen=i,plugin=PLUGIN,geometry=dict(x=i*1920,y=0,width=1920,height=1080),values={k:dict(present=True,value=v) for k,v in values.items()}) for i in range(2)])
        after=json.loads(json.dumps(before))
        for target in after['targets']: target['values']={k:dict(present=True,value=v) for k,v in new.items()}
        record=dict(schema=1,before=before,proposed=new,library='/home/example/Steam',wallpaper='456')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'record.json';path.write_text(json.dumps(record));original=path.read_bytes()
            with patch.object(app,'snapshot',side_effect=[before,after]),patch.object(app,'live_plan',return_value={'proposed':new}),patch.object(app,'evaluate',return_value={'ok':True}) as evaluate,patch.object(app.time,'sleep'),contextlib.redirect_stdout(io.StringIO()):
                app.run(path,False)
            self.assertEqual(evaluate.call_count,2)
            second=json.loads(evaluate.call_args_list[1].args[0].splitlines()[0][14:-1])
            self.assertEqual(second['before']['targets'][0]['values']['WallpaperSource']['value'],'')
            self.assertEqual(second['proposed'],new)
            self.assertEqual(path.read_bytes(),original)
