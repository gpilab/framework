## GPIArray Documentation

`GPIArray` is the new high-performance computing library powering GPI. Zero-copy NumPy integration, built-in FFT and linear algebra, automatic SIMD vectorization.

### Quick Navigation

| Topic | Link |
|-------|------|
| **What is GPIArray?** | [Architecture](01_Architechtre.md) |
| **Array creation & slicing** | [Data Structures](02_Data%20structure.md) |
| **Matrix math (SVD, MatMul, PCA)** | [Math Operations](03_Math.md) |
| **FFT transforms** | [FFTW Guide](04_FFTW.md) |
| **C++↔Python binding** | [Python Integration](05_Python_Integration.md) |
| **Build & compile** | [Build System](06_BuilsSystem.md) |

### 30-Second Start

**1. Write C++ code** (`MyModule_PYBIND11.cpp`):
```cpp
#include "GPIArray/GPIArray.hpp"
using namespace GPIArray;

Array<double> add(const Array<double>& a, const Array<double>& b) {
    return a + b;
}

PYBIND11_MODULE(MyModule, m) {
    m.def("add", &add);
}
```

**2. Build:**
```bash
gpi_make MyModule
```

**3. Use from Python:**
```python
import numpy as np, MyModule
result = MyModule.add(np.array([1,2,3]), np.array([4,5,6]))
# Zero-copy! Result: [5, 7, 9]
```

### Common Issues

- **Build fails?** → [Troubleshooting](gpi/include/GPIArray/06_BuilsSysten.md#65-troubleshooting)
- **Segfault?** → `gpi_make MyModule --debug` (bounds checking)
- **Type error in Python?** → [Type Mapping](gpi/include/GPIArray/05_Python_Integration.md#52-type-mapping-table)

---