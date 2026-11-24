import io
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

import numpy as np


ROOT = Path(__file__).resolve().parent.parent


@unittest.skipUnless(os.name == 'posix' and shutil.which('g++'),
                     'requires a C++ compiler and zlib')
class TestVoxelNativeWarnings(unittest.TestCase):
    def test_fill_and_compressed_array(self):
        source = r'''
#include "Voxel/Array.hpp"
#include "Voxel/cnpy.h"
#include <cassert>
#include <cmath>
#include <complex>

int main(int argc, char** argv) {
    assert(argc == 3);
    using C = std::complex<float>;
    Voxel::Array<C> values(4, 4);
    values.fill(C(3, 4));
    auto rows = values.slice(Voxel::S(0, 4, 2), Voxel::S::all());
    rows.fill(C(0, 0));
    assert(values(0, 0) == C(0, 0));
    assert(values(1, 0) == C(3, 4));
    assert(values(2, 3) == C(0, 0));
    Voxel::Array<float> floats(2);
    floats.fill(-0.0f);
    assert(std::signbit(floats(0)));

    auto arrays = cnpy::npz_load(argv[1]);
    assert(arrays.at("value").shape == std::vector<size_t>{3});
    const auto* data = arrays.at("value").data<int32_t>();
    assert(data[0] == 1 && data[1] == -2 && data[2] == 3);

    FILE* fp = fopen(argv[2], "rb");
    assert(fp);
    bool rejected = false;
    try { cnpy::load_the_npz_array(fp, 3, 128); }
    catch (const std::runtime_error&) { rejected = true; }
    fclose(fp);
    assert(rejected);
}
'''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cpp = root / 'test.cpp'
            cpp.write_text(source, encoding='utf-8')
            npy = io.BytesIO()
            np.save(npy, np.array([1, -2, 3], dtype=np.int32))
            archive = root / 'values.npz'
            with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('value.npy', npy.getvalue())
            bad = root / 'bad.deflate'
            bad.write_bytes(b'bad')
            binary = root / 'test'
            subprocess.run(
                ['g++', '-std=c++20', '-Wall', '-Wextra', '-Wpedantic',
                 '-Werror=unused-but-set-variable', '-Werror=class-memaccess',
                 '-I', str(ROOT / 'gpi' / 'include'), str(cpp), '-lz', '-o', str(binary)],
                check=True, capture_output=True, text=True)
            subprocess.run([str(binary), str(archive), str(bad)],
                           check=True, capture_output=True, text=True)


if __name__ == '__main__':
    unittest.main()
