import ast
from contextlib import redirect_stderr, redirect_stdout
import io
import os
from pathlib import Path
import sys
import tempfile
import traceback
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


SOURCE = Path(__file__).resolve().parent.parent / 'gpi' / 'make_pybind11.py'


class TestNativeToolchains(unittest.TestCase):
    def setUp(self):
        names = {'_configured_compiler', 'compile_cpp_module',
                 '_cuda_example_skip_reason', 'BuildConfiguration'}
        tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
        nodes = [node for node in tree.body
                 if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names]
        self.native_builder = type('NativeBuilder', (), {})
        self.torch_builder = type('TorchBuilder', (), {})
        self.setup = Mock()
        self.distribution = Mock()
        self.distribution.get_option_dict.return_value = {
            'compiler': ('distutils.cfg', 'mingw32')}
        self.namespace = {
            '__file__': str(SOURCE), 'os': os, 'sys': sys, 'tempfile': tempfile,
            'traceback': traceback,
            'platform': SimpleNamespace(system=lambda: 'Windows'),
            'Distribution': Mock(return_value=self.distribution),
            '_build_ext_msvc': self.native_builder,
            '_release_locked_output': Mock(), 'generate_python_stub': Mock(),
            'setup': self.setup,
            'Extension': lambda name, **options: SimpleNamespace(name=name, **options),
            'SUCCESS': 0, 'ERROR_FAILED_COMPILATION': 1,
            'Cl': SimpleNamespace(OKGR='', ESC='', FAIL='', OKBL=''),
            'find_nvcc': Mock(return_value='nvcc'),
            '_find_cl_exe_dir': Mock(return_value='msvc'),
        }
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), 'exec'),
             self.namespace)

    def test_configured_mingw_is_detected_and_msvc_override_uses_msvc_flags(self):
        with redirect_stdout(io.StringIO()):
            configuration = self.namespace['BuildConfiguration'].__new__(
                self.namespace['BuildConfiguration'])
            configuration._compiler = None
            self.assertTrue(configuration._detect_mingw())
            self.distribution.parse_config_files.assert_called()
            configuration._compiler = 'msvc'
            self.assertFalse(configuration._detect_mingw())
            configuration.options = SimpleNamespace(debug=False)
            configuration.extra_compile_args = []
            configuration.libraries = ['gomp']
            configuration._apply_compiler_flags()
        self.assertIn('/std:c++20', configuration.extra_compile_args)
        self.assertNotIn('-fopenmp', configuration.extra_compile_args)
        self.assertNotIn('gomp', configuration.libraries)

    def test_torch_forces_msvc_but_native_build_preserves_mingw(self):
        for torch in (False, True):
            with self.subTest(torch=torch), patch.dict(os.environ, {'CXX': 'g++'}):
                builder = self.torch_builder if torch else self.native_builder
                self.namespace['_add_libtorch_support'] = Mock(
                    return_value=([], [], [], [], [], builder))
                seen_cxx = []
                self.setup.side_effect = lambda **kwargs: seen_cxx.append(os.environ['CXX'])
                self.assertEqual(self.namespace['compile_cpp_module']('example', []), 0)
                options = self.setup.call_args.kwargs
                expected_compiler = 'msvc' if torch else 'mingw32'
                self.assertIn('--compiler=' + expected_compiler, options['script_args'])
                flags = options['ext_modules'][0].extra_compile_args
                if torch:
                    self.assertTrue(any(flag.startswith('/FI') for flag in flags))
                    self.assertEqual(seen_cxx, ['cl'])
                else:
                    self.assertEqual(flags[0], '-include')
                    self.assertFalse(any(flag.startswith('/FI') for flag in flags))
                    self.assertEqual(seen_cxx, ['g++'])
                self.assertEqual(os.environ['CXX'], 'g++')

    def test_cuda_examples_skip_only_when_requirements_are_missing(self):
        target = {
            'full_filename': str(SOURCE.parent.parent / 'gpi_core' / 'examples'
                                 / 'PyTorch' / 'CustomCUDA' / 'cuda_basics_bind.cpp'),
            'cuda_sources': ['kernel.cu'],
        }
        torch = SimpleNamespace(version=SimpleNamespace(cuda='12.6'),
                                cuda=SimpleNamespace(is_available=Mock(return_value=True)))
        skip_reason = self.namespace['_cuda_example_skip_reason']
        with patch.dict(sys.modules, {'torch': torch}):
            self.assertIsNone(skip_reason(target))
            torch.cuda.is_available.return_value = False
            self.assertIn('GPU or driver', skip_reason(target))
            torch.cuda.is_available.return_value = True
            torch.version.cuda = None
            self.assertIn('without CUDA', skip_reason(target))
            torch.version.cuda = '12.6'
            self.namespace['find_nvcc'].return_value = None
            self.assertIn('nvcc', skip_reason(target))
            self.namespace['find_nvcc'].return_value = 'nvcc'
            self.namespace['_find_cl_exe_dir'].return_value = None
            self.assertIn('MSVC', skip_reason(target))
        with patch.dict(sys.modules, {'torch': None}):
            self.assertIn('not installed', skip_reason(target))
            production = dict(target, full_filename=str(SOURCE.parent / 'production_bind.cpp'))
            self.assertIsNone(skip_reason(production))
            self.assertIsNone(skip_reason(dict(target, cuda_sources=[])))

    def test_cuda_objects_force_msvc_without_libtorch(self):
        self.namespace['_add_libtorch_support'] = Mock(
            return_value=([], [], [], [], [], self.native_builder))
        self.assertEqual(self.namespace['compile_cpp_module'](
            'cuda_module', [], extra_objects=['kernel.obj']), 0)
        options = self.setup.call_args.kwargs
        self.assertIn('--compiler=msvc', options['script_args'])
        extension = options['ext_modules'][0]
        self.assertEqual(extension.extra_objects, ['kernel.obj'])
        self.assertTrue(any(flag.startswith('/FI') for flag in extension.extra_compile_args))

    def test_build_failure_diagnostics_are_visible(self):
        self.namespace['_add_libtorch_support'] = Mock(
            return_value=([], [], [], [], [], self.native_builder))
        self.setup.side_effect = RuntimeError('compiler diagnostic')
        output = io.StringIO()
        with redirect_stderr(output):
            self.assertEqual(self.namespace['compile_cpp_module']('broken', []), 1)
        self.assertIn('compiler diagnostic', output.getvalue())


if __name__ == '__main__':
    unittest.main()
