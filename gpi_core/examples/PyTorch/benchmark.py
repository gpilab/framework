# Author: Guru Krishanmoorthy
# Date: Nov 2026

from time import perf_counter

import gpi


def compare_cpu_gpu(backend, elements, repeats):
    """Compare warmed in-place scaling without changing a node's input or output."""
    import torch

    if not 1 <= elements <= 16000000:
        raise ValueError('Benchmark Elements must be between 1 and 16000000.')
    if not 1 <= repeats <= 100:
        raise ValueError('Benchmark Repeats must be between 1 and 100.')

    if backend == 'pytorch':
        operation = torch.Tensor.mul_
    elif backend == 'libtorch':
        from gpi_core.examples.PyTorch import libtorch_basics
        operation = libtorch_basics.benchmark_scale_inplace
    elif backend == 'cuda':
        from gpi_core.examples.PyTorch.CustomCUDA import cuda_basics
        operation = cuda_basics.benchmark_scale_inplace
    else:
        raise ValueError(f'Unknown benchmark backend: {backend}')

    # A small fixed factor avoids overflow when repeating an in-place operation.
    factor = 1.0001
    cpu_data = torch.ones(elements, dtype=torch.float32)
    operation(cpu_data, factor)
    cpu_data.fill_(1.0)
    start = perf_counter()
    for _ in range(repeats):
        operation(cpu_data, factor)
    cpu_ms = (perf_counter() - start) * 1000 / repeats

    expected = torch.ones((), dtype=torch.float32)
    for _ in range(repeats):
        expected.mul_(factor)
    if not torch.all(cpu_data == expected.item()).item():
        raise RuntimeError('CPU benchmark produced an incorrect result.')
    cpu_data.fill_(1.0)

    report = (
        f'CPU/GPU comparison: {backend}\n'
        f'Elements: {elements:,} | float32 | {elements * 4 / 1048576:.2f} MiB\n'
        f'Repeats: {repeats} | CPU threads: {torch.get_num_threads()}\n'
        f'Operation: in-place multiply by {factor}; warm-up excluded.\n'
        'Uses private generated arrays, independent of input, Factor, and Device.\n'
        f'CPU compute: {cpu_ms:.6f} ms/op'
    )
    device = gpi.torch_auto_device()
    if not device.startswith('cuda:'):
        return report + '\nCUDA GPU: unavailable or disabled; only CPU was measured.'

    with gpi.gpu_exclusive():
        gpu_data = cpu_data.to(device)
        operation(gpu_data, factor)
        gpu_data.fill_(1.0)
        torch.cuda.synchronize(device)

        start = perf_counter()
        for _ in range(repeats):
            operation(gpu_data, factor)
        torch.cuda.synchronize(device)
        gpu_ms = (perf_counter() - start) * 1000 / repeats
        if not torch.all(gpu_data == expected.item()).item():
            raise RuntimeError('GPU benchmark produced an incorrect result.')

        torch.cuda.synchronize(device)
        start = perf_counter()
        for _ in range(repeats):
            gpu_copy = cpu_data.to(device)
        torch.cuda.synchronize(device)
        upload_ms = (perf_counter() - start) * 1000 / repeats

        start = perf_counter()
        for _ in range(repeats):
            host_copy = gpu_data.cpu()
        torch.cuda.synchronize(device)
        download_ms = (perf_counter() - start) * 1000 / repeats

        start = perf_counter()
        for _ in range(repeats):
            gpu_copy = cpu_data.to(device)
            operation(gpu_copy, factor)
            host_copy = gpu_copy.cpu()
        torch.cuda.synchronize(device)
        roundtrip_ms = (perf_counter() - start) * 1000 / repeats
        if not torch.all(host_copy == torch.tensor(factor, dtype=torch.float32).item()).item():
            raise RuntimeError('GPU round-trip benchmark produced an incorrect result.')

        report += (
            f'\nGPU: {device} ({torch.cuda.get_device_name(device)})\n'
            f'GPU resident compute: {gpu_ms:.6f} ms/op\n'
            f'Host -> GPU: {upload_ms:.6f} ms/transfer\n'
            f'GPU -> host: {download_ms:.6f} ms/transfer\n'
            f'GPU end-to-end: {roundtrip_ms:.6f} ms/op\n'
            f'Compute speedup (CPU/GPU): {cpu_ms / gpu_ms:.3f}x\n'
            f'End-to-end speedup (CPU/GPU): {cpu_ms / roundtrip_ms:.3f}x\n'
            'Compute uses resident buffers; allocation and transfers are excluded.\n'
            'Times are host-measured averages, including dispatch and GPU synchronization.\n'
            'Transfers use ordinary pageable host memory and include allocation.\n'
            'End-to-end includes upload, multiplication, and download.'
        )
    return report
