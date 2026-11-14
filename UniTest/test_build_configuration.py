import ast
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parent.parent / 'gpi' / 'make_pybind11.py'


class TestBuildConfiguration(unittest.TestCase):
    def setUp(self):
        tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
        discovery = next(node for node in tree.body
                         if isinstance(node, ast.FunctionDef)
                         and node.name == 'get_search_directories')
        configuration = next(node for node in tree.body
                             if isinstance(node, ast.ClassDef)
                             and node.name == 'BuildConfiguration')
        loader = next(node for node in configuration.body
                      if isinstance(node, ast.FunctionDef)
                      and node.name == '_load_user_config')
        self.settings = SimpleNamespace(
            GPI_LIBRARY_PATH=[], MAKE_LIBS=['custom'],
            MAKE_INC_DIRS=['headers'], MAKE_LIB_DIRS=['libraries'],
            MAKE_CFLAGS=['-DCUSTOM'])
        namespace = {
            'os': os, 'Config': self.settings,
            'findLibrariesInPath': lambda path: [],
        }
        # Exercise build settings without importing Qt or compiler dependencies.
        isolated = ast.Module(body=[discovery, loader], type_ignores=[])
        exec(compile(isolated, str(SOURCE), 'exec'), namespace)
        self.discover = namespace['get_search_directories']
        self.load_settings = namespace[loader.name]
        self.output = redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def test_existing_gpirc_is_not_opened(self):
        with tempfile.TemporaryDirectory() as home:
            legacy = Path(home) / '.gpirc'
            legacy.write_text('LIB_DIRS=' + home, encoding='utf-8')
            with patch('os.path.expanduser', return_value=str(legacy)), \
                    patch('builtins.open') as open_file:
                self.discover(home, False, True, working_dir=home)
            open_file.assert_not_called()

    def test_json_library_paths_are_used_unless_config_is_ignored(self):
        with tempfile.TemporaryDirectory() as root:
            project = Path(root) / 'project'
            library = Path(root) / 'nodes'
            project.mkdir()
            library.mkdir()
            self.settings.GPI_LIBRARY_PATH = [str(library)]
            self.assertIn(str(library), self.discover(
                str(project), False, True, working_dir=str(project)))
            self.assertNotIn(str(library), self.discover(
                str(project), True, True, working_dir=str(project)))

    def test_json_build_settings_are_used_unless_config_is_ignored(self):
        for ignored in (False, True):
            with self.subTest(ignored=ignored):
                build = SimpleNamespace(
                    options=SimpleNamespace(ignore_config=ignored),
                    libraries=[], include_dirs=[], library_dirs=[],
                    extra_compile_args=[])
                self.load_settings(build)
                self.assertEqual(build.libraries, [] if ignored else ['custom'])
                self.assertEqual(build.include_dirs, [] if ignored else ['headers'])
                self.assertEqual(build.library_dirs, [] if ignored else ['libraries'])
                self.assertEqual(build.extra_compile_args, [] if ignored else ['-DCUSTOM'])


class TestLegacyBuildDiscovery(unittest.TestCase):
    def setUp(self):
        source = SOURCE.with_name('make.py')
        tree = ast.parse(source.read_text(encoding='utf-8'))
        nodes = [
            node for node in tree.body
            if (isinstance(node, ast.FunctionDef) and node.name == 'targetWalk')
            or (isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == '_SKIP_DIRS'
                        for target in node.targets))
        ]
        namespace = {'os': os}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), namespace)
        self.discover = namespace['targetWalk']

    def test_recursive_build_selects_only_legacy_native_extensions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ('Node_GPI.py', 'helper.py', '__init__.py',
                         'native_PyMOD.cpp', 'modern_bind.cpp', 'helper.cpp',
                         'nested/other_PyMOD.cpp', 'nested/library.py',
                         'build/stale_PyMOD.cpp'):
                path = root.joinpath(*name.split('/'))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('', encoding='utf-8')
            with patch('os.getcwd', return_value=folder):
                targets = self.discover(10)
            self.assertEqual(
                {(Path(target['pth']) / (target['fn'] + target['ext'])).relative_to(root)
                 for target in targets},
                {Path('native_PyMOD.cpp'), Path('nested') / 'other_PyMOD.cpp'})

    def test_python_only_library_has_no_build_targets(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'helper.py').write_text('value = 1\n', encoding='utf-8')
            with patch('os.getcwd', return_value=folder):
                self.assertEqual(self.discover(10), [])


if __name__ == '__main__':
    unittest.main()
