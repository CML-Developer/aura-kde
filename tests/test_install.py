import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('installer',Path(__file__).resolve().parents[1]/'scripts/install.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)

class InstallTests(unittest.TestCase):
    def invoke(self,prefix,remove=False):
        from pathlib import Path as _Path
        args=['install','--prefix',str(prefix)]+(['--uninstall'] if remove else [])
        with patch.object(sys,'argv',args),\
             patch.object(installer,'find_binary',return_value=_Path('/fake/aura')),\
             patch.object(installer,'package',return_value={'bin/aura-kde-lab':(b'owned',0o755)}),\
             contextlib.redirect_stdout(io.StringIO()):
            installer.main()
    def test_idempotent_install_and_scoped_removal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);foreign=root/'notes.txt';foreign.write_text('keep')
            self.invoke(root);self.invoke(root)
            self.assertEqual((root/'bin/aura-kde-lab').read_bytes(),b'owned')
            self.invoke(root,True)
            self.assertTrue(foreign.exists())
            self.assertFalse((root/'bin/aura-kde-lab').exists())
    def test_preserves_modified_and_unowned_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.invoke(root)
            (root/'bin/aura-kde-lab').write_text('user changes')
            with self.assertRaises(ValueError):self.invoke(root,True)
            self.assertEqual((root/'bin/aura-kde-lab').read_text(),'user changes')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'bin').mkdir();(root/'bin/aura-kde-lab').write_text('foreign')
            with self.assertRaises(ValueError):self.invoke(root)
