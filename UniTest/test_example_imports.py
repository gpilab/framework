import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parent.parent


class TestInstalledExampleImports(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.stage = Path(temporary.name)
        core = self.stage / 'gpi_core'
        core.mkdir()
        shutil.copy2(ROOT / 'gpi_core' / '__init__.py', core / '__init__.py')
        examples = ROOT / 'gpi_core' / 'examples'
        for source in examples.rglob('*.py'):
            if 'build' in source.parts:
                continue
            destination = core / 'examples' / source.relative_to(examples)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    def run_isolated(self, code):
        prelude = """
            import importlib.abc
            from pathlib import Path
            import runpy
            import sys

            sys.path.insert(0, sys.argv[1])

            class RejectExternalExamples(importlib.abc.MetaPathFinder):
                def find_spec(self, fullname, path=None, target=None):
                    if fullname == 'gpi_examples' or fullname.startswith('gpi_examples.'):
                        raise ModuleNotFoundError('External examples must not be required')

            sys.meta_path.insert(0, RejectExternalExamples())
            examples = Path(sys.argv[1]) / 'gpi_core' / 'examples'
        """
        result = subprocess.run(
            [sys.executable, '-I', '-c', textwrap.dedent(prelude) + textwrap.dedent(code),
             str(self.stage)],
            cwd=self.stage, capture_output=True, text=True, timeout=60,
            env=dict(os.environ, GPI_WORKER_MODE='1',
                     OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1'))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_nodes_load_without_external_library_or_native_extensions(self):
        self.run_isolated("""
            loader = importlib.import_module('gpi.loader')

            nodes = sorted(examples.rglob('*_GPI.py'))
            assert nodes, 'No example nodes discovered'
            for path in nodes:
                node = loader.loadMod(str(path))
                assert node is not None, loader._last_load_error
                assert hasattr(node, 'ExternalNode'), str(path)
        """)

    def test_compute_and_benchmark_import_packaged_backends(self):
        self.run_isolated("""
            from types import ModuleType
            import gpi

            sys.modules['torch'] = ModuleType('torch')

            class BackendSelected(Exception):
                pass

            class ObserveBackendImports(importlib.abc.MetaPathFinder):
                def find_spec(self, fullname, path=None, target=None):
                    if fullname.startswith('gpi_core.examples.') and (
                            '.voxel_' in fullname or fullname.endswith('.libtorch_basics')
                            or fullname.endswith('.cuda_basics')):
                        raise BackendSelected(fullname)

            sys.meta_path.insert(0, ObserveBackendImports())
            backends = {
                'Scale': 'Voxel.voxel_scale',
                'ArrayBasics': 'Voxel.voxel_basics',
                'ArrayOptions': 'Voxel.voxel_array_options',
                'NumpyFiles': 'Voxel.voxel_files',
                'TransformOptions': 'Voxel.voxel_transform_options',
                'LibTorchBasics': 'PyTorch.libtorch_basics',
                'CustomCUDA': 'PyTorch.CustomCUDA.cuda_basics',
            }

            def expect_backend(operation, expected):
                try:
                    operation()
                except BackendSelected as error:
                    assert str(error) == 'gpi_core.examples.' + expected, str(error)
                else:
                    raise AssertionError('Expected native backend import: ' + expected)

            for path in examples.rglob('*_GPI.py'):
                name = path.stem.removesuffix('_GPI')
                if name in backends:
                    node = runpy.run_path(str(path))
                    expect_backend(lambda: node['ExternalNode'].compute(None), backends[name])

            from gpi_core.examples.PyTorch import benchmark
            for name in ('libtorch', 'cuda'):
                target = ('PyTorch.libtorch_basics' if name == 'libtorch'
                          else 'PyTorch.CustomCUDA.cuda_basics')
                expect_backend(lambda: benchmark.compare_cpu_gpu(name, 1, 1), target)
        """)


if __name__ == '__main__':
    unittest.main()
