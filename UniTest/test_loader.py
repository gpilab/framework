import importlib
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


class TestDependencyReload(unittest.TestCase):
    def setUp(self):
        package = ModuleType('_gpi_loader_test')
        package.__path__ = []
        defines = ModuleType('_gpi_loader_test.defines')
        defines.GPI_PYMOD_EXTS = ['.py', '.pyc']
        logger = ModuleType('_gpi_loader_test.logger')
        self.log = Mock()
        logger.manager = SimpleNamespace(getLogger=Mock(return_value=self.log))
        self.modules = patch.dict(sys.modules, {
            package.__name__: package,
            defines.__name__: defines,
            logger.__name__: logger,
        })
        self.modules.start()
        self.addCleanup(self.modules.stop)
        path = Path(__file__).resolve().parent.parent / 'gpi' / 'loader.py'
        spec = importlib.util.spec_from_file_location('_gpi_loader_test.loader', path)
        self.loader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.loader)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        node_dir = self.root / 'GPI'
        node_dir.mkdir()
        self.node = str(node_dir / 'Node_GPI.py')

    def test_path_registered_dependency_reloads_in_place(self):
        helper = self.root / 'DownloadFile_GPI.py'
        helper.write_text('VALUE = 1\n', encoding='utf-8')
        module = self.loader.loadMod(str(helper))
        self.assertIsNotNone(module)
        helper.write_text('VALUE = 12345\n', encoding='utf-8')
        self.assertTrue(self.loader._reload_node_dependencies(self.node, 'node'))
        self.assertEqual(module.VALUE, 12345)
        self.assertIs(sys.modules[str(helper.with_suffix(''))], module)
        self.log.warn.assert_not_called()

    def test_normally_imported_helper_still_reloads(self):
        helper = self.root / '_gpi_reload_helper.py'
        helper.write_text('VALUE = 1\n', encoding='utf-8')
        with patch.object(sys, 'path', [str(self.root)] + sys.path):
            module = importlib.import_module('_gpi_reload_helper')
            helper.write_text('VALUE = 12345\n', encoding='utf-8')
            self.assertTrue(self.loader._reload_node_dependencies(self.node, 'node'))
        self.assertEqual(module.VALUE, 12345)
        self.log.warn.assert_not_called()

    def test_path_registered_dependency_failure_is_reported(self):
        helper = self.root / 'Broken_GPI.py'
        helper.write_text('VALUE = 1\n', encoding='utf-8')
        self.assertIsNotNone(self.loader.loadMod(str(helper)))
        helper.write_text("raise RuntimeError('reload failed')\n", encoding='utf-8')
        self.assertFalse(self.loader._reload_node_dependencies(self.node, 'node'))
        self.log.warn.assert_called_once()
        self.assertIn('RuntimeError: reload failed', self.log.warn.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
