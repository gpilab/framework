"""Cartesian reconstruction and noise-covariance SNR for Philips list/data."""

import gpi
import numpy as np


def estimate_noise_covariance(noise, noise_scale=1.0):
    """Estimate per-component covariance: Psi = E[(n-mean)(n-mean)^H] / 2.

    noise_scale multiplies the noise standard deviation, not its variance.
    """
    noise = np.asarray(noise)
    if noise.ndim != 2 or not np.iscomplexobj(noise):
        raise ValueError('Noise must be a complex (coil, sample) array.')
    if noise.shape[0] < 1 or noise.shape[1] <= noise.shape[0]:
        raise ValueError('More independent noise samples than coils are required.')
    if not np.isfinite(noise).all() or not np.isfinite(noise_scale) or noise_scale <= 0:
        raise ValueError('Noise and its positive scale must be finite.')
    centered = noise.astype(np.complex128)
    centered -= centered.mean(axis=1, keepdims=True)
    covariance = centered @ centered.conj().T
    covariance *= noise_scale ** 2 / (2 * (noise.shape[1] - 1))
    if np.any(covariance.diagonal().real <= 0):
        raise ValueError('Each coil must have nonzero noise variance.')
    return covariance


def calculate_snr(images, covariance, bias_correction=True, covariance_floor=1e-6):
    """Compute per-coil and covariance-whitened RSS SNR, retaining dynamics.

    images: complex (coil, dynamic, spatial...) values. covariance: matching
    per-component image noise covariance (dynamic, coil, coil).
    Bias correction subtracts expected noise POWER before taking a square root;
    it is not an unbiased amplitude estimator and clips negative power to zero.
    """
    images = np.asarray(images)
    covariance = np.asarray(covariance, dtype=np.complex128)
    if images.ndim not in (4, 5) or not np.iscomplexobj(images):
        raise ValueError('Images must be complex (coil, dynamic, y, x) or (coil, dynamic, z, y, x).')
    coils, dynamics = images.shape[:2]
    if covariance.shape != (dynamics, coils, coils):
        raise ValueError('Image covariance dimensions do not match coils/dynamics.')
    if not np.isfinite(covariance_floor) or not 0 < covariance_floor < 1:
        raise ValueError('Covariance eigenvalue floor must be between 0 and 1.')
    if not np.isfinite(covariance).all():
        raise ValueError('Covariance must be finite.')
    voxel_count = int(np.prod(images.shape[2:]))
    coil_snr = np.empty((coils, dynamics, voxel_count), dtype=np.float32)
    combined_snr = np.empty((dynamics, voxel_count), dtype=np.float32)
    rss = np.empty_like(combined_snr)
    details = []
    for dynamic in range(dynamics):
        matrix = covariance[dynamic]
        if not np.allclose(matrix, matrix.conj().T):
            raise ValueError('Noise covariance must be Hermitian.')
        eigenvalues, vectors = np.linalg.eigh(matrix)
        if eigenvalues[-1] <= 0 or eigenvalues[0] < -1e-8 * eigenvalues[-1]:
            raise ValueError('Noise covariance must be positive semidefinite and nonzero.')
        diagonal = matrix.diagonal().real
        if np.any(diagonal <= 0):
            raise ValueError('Each coil must have positive image noise variance.')
        floored = np.maximum(eigenvalues, eigenvalues[-1] * covariance_floor)
        whitener = vectors.conj().T / np.sqrt(floored)[:, None]
        noise_power = 2 * float(np.sum(np.maximum(eigenvalues, 0) / floored))
        frame = images[:, dynamic].reshape(coils, voxel_count)
        for start in range(0, voxel_count, 65536):
            stop = min(start + 65536, voxel_count)
            block = np.asarray(frame[:, start:stop], dtype=np.complex128)
            if not np.isfinite(block).all():
                raise ValueError('Images must be finite.')
            power = np.abs(block) ** 2
            coil_power = power / diagonal[:, None]
            whitened_power = np.sum(np.abs(whitener @ block) ** 2, axis=0)
            if bias_correction:
                coil_power -= 2
                whitened_power -= noise_power
            coil_snr[:, dynamic, start:stop] = np.sqrt(np.maximum(coil_power, 0))
            combined_snr[dynamic, start:stop] = np.sqrt(np.maximum(whitened_power, 0))
            rss[dynamic, start:stop] = np.sqrt(power.sum(axis=0))
        details.append({'eigenvalues': eigenvalues.tolist(),
                        'regularized_eigenvalues': floored.tolist(),
                        'combined_noise_power': noise_power,
                        'coil_noise_std': np.sqrt(diagonal).tolist()})
    return {'coil_snr': coil_snr.reshape(images.shape),
            'combined_snr': combined_snr.reshape(images.shape[1:]),
            'rss': rss.reshape(images.shape[1:]), 'covariance_details': details}


def estimate_sensitivity_maps(images, smoothing=2.0, mask_fraction=0.05):
    """Estimate relative complex sensitivities from fully sampled coil images.

    Gaussian smoothing is in image voxels. The RSS-relative support threshold
    assumes negligible object signal outside the mask; maps are approximate,
    especially near boundaries, signal voids and rapidly varying object phase.
    """
    from scipy.ndimage import gaussian_filter

    images = np.asarray(images)
    if images.ndim not in (3, 4) or not np.iscomplexobj(images):
        raise ValueError('Sensitivity estimation needs complex (coil, [z,] y, x) images.')
    if not np.isfinite(images).all() or not np.isfinite(smoothing) or smoothing < 0:
        raise ValueError('Coil images must be finite and smoothing must be nonnegative.')
    if not np.isfinite(mask_fraction) or not 0 <= mask_fraction < 1:
        raise ValueError('Sensitivity mask fraction must be in [0, 1).')
    power = np.zeros(images.shape[1:], dtype=np.float64)
    norm_power = np.zeros_like(power)
    maps = np.empty(images.shape, dtype=np.complex64)
    for coil, image in enumerate(images):
        power += image.real.astype(np.float64) ** 2
        power += image.imag.astype(np.float64) ** 2
        maps[coil] = (gaussian_filter(image.real, smoothing)
                      + 1j * gaussian_filter(image.imag, smoothing))
        norm_power += maps[coil].real.astype(np.float64) ** 2
        norm_power += maps[coil].imag.astype(np.float64) ** 2
    rss = np.sqrt(power)
    norm = np.sqrt(norm_power)
    support = (rss > mask_fraction * rss.max()) & (norm > 0)
    np.divide(maps, norm[None], out=maps, where=support[None])
    maps[:, ~support] = 0
    return maps, support


def _g_factor_dimensions(spatial_shape, acceleration_y, acceleration_z):
    for factor in (acceleration_y, acceleration_z):
        if not isinstance(factor, (int, np.integer)) or factor < 1:
            raise ValueError('g-factor acceleration factors must be positive integers.')
    if len(spatial_shape) == 2 and acceleration_z != 1:
        raise ValueError('R z must be 1 for 2D data.')
    depth, height, width = spatial_shape if len(spatial_shape) == 3 else (1,) + tuple(spatial_shape)
    if height % acceleration_y or depth % acceleration_z:
        valid_y = [factor for factor in range(1, min(height, 32) + 1) if height % factor == 0]
        valid_z = [factor for factor in range(1, min(depth, 32) + 1) if depth % factor == 0]
        raise ValueError(
            'Native y={}, z={} are not divisible by R y={}, R z={}. '
            'Compatible R y: {}; R z: {}. No padding or cropping was applied.'.format(
                height, depth, acceleration_y, acceleration_z, valid_y, valid_z))
    return depth, height, width


def calculate_g_factor(sensitivities, covariance, acceleration_y=1, acceleration_z=1,
                       support=None, covariance_floor=1e-6):
    """Predict uniform Cartesian, unregularized SENSE g from A = S^H Psi^-1 S.

    g_i = sqrt(diag(inv(A))_i * diag(A)_i). Directions use native image axes.
    Dimensions must be divisible by the integer acceleration factors. Masked
    locations are assumed signal-free. Output is NaN outside support and inf
    for singular alias groups; no pseudoinverse or SENSE regularizer is used.
    """
    maps = np.asarray(sensitivities)
    if maps.ndim not in (3, 4) or not np.iscomplexobj(maps) or not np.isfinite(maps).all():
        raise ValueError('Sensitivities must be finite complex (coil, [z,] y, x) maps.')
    coils = maps.shape[0]
    depth, height, width = _g_factor_dimensions(maps.shape[1:], acceleration_y, acceleration_z)
    matrix = np.asarray(covariance, dtype=np.complex128)
    if (matrix.shape != (coils, coils) or not np.isfinite(matrix).all()
            or not np.allclose(matrix, matrix.conj().T)):
        raise ValueError('g-factor needs a finite Hermitian coil noise covariance.')
    if not np.isfinite(covariance_floor) or not 0 < covariance_floor < 1:
        raise ValueError('Covariance eigenvalue floor must be between 0 and 1.')
    eigenvalues, vectors = np.linalg.eigh(matrix)
    if eigenvalues[-1] <= 0 or eigenvalues[0] < -1e-8 * eigenvalues[-1]:
        raise ValueError('Noise covariance must be positive semidefinite and nonzero.')
    floored = np.maximum(eigenvalues, eigenvalues[-1] * covariance_floor)
    whitener = vectors.conj().T / np.sqrt(floored)[:, None]
    if support is None:
        support = np.any(np.abs(maps) > 0, axis=0)
    support = np.asarray(support, dtype=bool)
    if support.shape != maps.shape[1:]:
        raise ValueError('g-factor support must match the spatial sensitivity-map shape.')
    result = np.full(support.size, np.nan, dtype=np.float32)
    support_flat = support.reshape(-1)
    result[support_flat] = np.inf
    folded_y, folded_z = height // acceleration_y, depth // acceleration_z
    offsets = np.array([z * folded_z * height * width + y * folded_y * width
                        for z in range(acceleration_z) for y in range(acceleration_y)])
    aliases = len(offsets)
    group_count = folded_z * folded_y * width
    batch_size = max(1, min(2048, 1048576 // max(coils * aliases, aliases ** 2)))
    flat_maps = maps.reshape(coils, -1)
    for start in range(0, group_count, batch_size):
        group = np.arange(start, min(start + batch_size, group_count))
        base = ((group // (folded_y * width)) * height * width
                + (group // width % folded_y) * width + group % width)
        indices = base[:, None] + offsets[None]
        active = support_flat[indices]
        counts = active.sum(axis=1)
        candidates = (counts > 0) & (counts <= coils)
        indices = indices[candidates]
        active = active[candidates]
        if not len(indices):
            continue
        encoding = (whitener @ flat_maps[:, indices].reshape(coils, -1))
        encoding = encoding.reshape(coils, len(indices), aliases).transpose(1, 0, 2)
        norm = np.sqrt(np.sum(np.abs(encoding) ** 2, axis=1))
        active &= norm > 0
        np.divide(encoding, norm[:, None, :], out=encoding, where=norm[:, None, :] > 0)
        encoding *= active[:, None, :]
        gram = encoding.conj().transpose(0, 2, 1) @ encoding
        diagonal_indices = np.arange(aliases)
        gram[:, diagonal_indices, diagonal_indices] = 1
        values, basis = np.linalg.eigh(gram)
        nonsingular = values[:, 0] > 1e-10 * values[:, -1]
        if nonsingular.any():
            inverse_diagonal = np.sum(
                np.abs(basis[nonsingular]) ** 2 / values[nonsingular, None, :], axis=2)
            factors = np.sqrt(np.maximum(inverse_diagonal, 1))
            selected = active[nonsingular]
            result[indices[nonsingular][selected]] = factors[selected]
    return result.reshape(support.shape)


def _reconstruct_readout_pair(grid, crops):
    """Return full-intensity mean and half-difference of aligned readout halves."""
    length = grid.shape[-1]
    if length % 2:
        raise ValueError('Odd/even reconstruction requires an even readout grid size.')
    half_length = length // 2
    positions = np.arange(half_length) - half_length // 2
    images = []
    for parity in (0, 1):
        image = np.fft.fftshift(np.fft.fftn(np.fft.ifftshift(grid[..., parity::2])))
        offset = parity - half_length % 2
        phase = np.exp(-2j * np.pi * offset * positions / length).astype(np.complex64)
        image *= 2 * phase
        images.append(image[tuple(crops[:-1]) + (slice(None),)])
    return (images[0] + images[1]) * 0.5, (images[0] - images[1]) * 0.5


def reconstruct_cartesian(raw, noise, metadata, remove_oversampling=True, noise_scale=1.0,
                          use_rf_off=False, retain_noise=False, use_readout_split=False):
    """Reconstruct Cartesian images with NOI, RF-off, or split-readout noise.

    Supports one mix/echo/location/average at a time, without parallel imaging,
    trajectory gridding, partial-Fourier recovery or phase correction. Spatial
    grids use nominal resolution times oversampling when supplied by the header.
    With use_rf_off, dynamic index 1 supplies image-domain noise covariance
    after the same FFT, signal sampling mask and crop as dynamic index 0.
    retain_noise keeps both reconstructed dynamics for downstream RSS output.
    Noise samples must have the same gain/bandwidth as STD, or be rescaled.
    use_readout_split uses only dynamic index 0 and requires a contiguous 2x
    oversampled readout; zero-filling to the reconstruction matrix is allowed.
    Its phase-aligned complex mean and half-difference
    have matched noise covariance only for uncorrelated, equal-variance
    interleaves; the object must fit within the retained half-FOV.
    """
    if use_readout_split and use_rf_off:
        raise ValueError('Select either RF-off or odd/even readout noise, not both.')
    if use_readout_split and not remove_oversampling:
        raise ValueError('Odd/even readout SNR requires Remove Oversampling.')
    if metadata.get('propeller', 'None') != 'None' or metadata.get('fft_applied', False):
        raise ValueError('Input must be untransformed, non-Propeller Cartesian ReadDataList data.')
    descriptions = metadata['outputs']
    description = descriptions['STD']
    noise_description = descriptions.get('NOI')
    if not use_rf_off and not use_readout_split and noise_description is None:
        raise ValueError('ReadDataList metadata has no NOI noise description.')
    standard_axes = ('chan', 'mix', 'dyn', 'card', 'extr1', 'extr2', 'echo',
                     'aver', 'loca', 'kz', 'ky', 'samp')
    shape = tuple(description['unsqueezed_shape'])
    if len(shape) != len(standard_axes):
        raise ValueError('Unsupported STD axis layout; disable Propeller reshaping.')
    raw = np.asarray(raw)
    if not np.iscomplexobj(raw) or tuple(raw.shape) != tuple(description['shape']):
        raise ValueError('Raw array shape/type does not match the STD metadata.')
    values = description['index_values']
    for axis, size in zip(standard_axes[:-1], shape[:-1]):
        if len(values[axis]) != size or len(set(values[axis])) != size:
            raise ValueError('Invalid index values for {}.'.format(axis))
    retained = ('chan', 'dyn', 'kz', 'ky', 'samp')
    selectors = []
    for axis, size in zip(standard_axes, shape):
        if axis not in retained and size != 1:
            raise ValueError('Select one {} before ComputeSNR.'.format(axis))
        selectors.append(slice(None) if axis in retained else 0)
    source = raw.reshape(shape)[tuple(selectors)]
    coils, dynamics, kz_count, ky_count, samples = source.shape
    if use_readout_split:
        source = source[:, :1]
        dynamics = 1
    elif dynamics != 2:
        raise ValueError('Exactly two dynamic scans are required.')
    if not use_rf_off and not use_readout_split:
        noise = np.asarray(noise)
        if not np.iscomplexobj(noise) or tuple(noise.shape) != tuple(noise_description['shape']):
            raise ValueError('Noise array shape/type does not match the NOI metadata.')
        noise = noise.reshape(noise_description['unsqueezed_shape'])
        noise_channels = noise_description['index_values']['chan']
        try:
            noise = noise[[noise_channels.index(channel) for channel in values['chan']]]
        except ValueError as error:
            raise ValueError('Every STD coil needs a matching NOI channel ID.') from error

    parameters = {}
    for line in metadata['list_text'].splitlines():
        fields, separator, text_value = line.partition(':')
        fields = fields.split()
        if separator and len(fields) >= 5 and fields[0] == '.':
            key = (int(fields[1]), int(fields[2]), int(fields[3]), ' '.join(fields[4:]))
            parameters[key] = text_value.split()
    mix, echo = values['mix'][0], values['echo'][0]

    def parameter(name, default=None, is_mix_parameter=False):
        key = (mix, 0 if is_mix_parameter else echo, 0, name)
        entry = parameters.get(key)
        if entry is None:
            if default is None:
                raise ValueError('Missing header parameter {}.'.format(name))
            return default
        return [float(value) for value in entry]

    dimensions = int(parameter('number_of_encoding_dimensions',
                               [3 if kz_count > 1 else 2], True)[0])
    if dimensions not in (2, 3) or (dimensions == 2 and kz_count != 1):
        raise ValueError('Only Cartesian 2D and 3D acquisitions are supported.')
    coordinates = {'ky': np.asarray(values['ky'], dtype=np.int64),
                   'kz': np.asarray(values['kz'], dtype=np.int64)}
    kx_range = parameter('kx_range', [-samples // 2, samples - samples // 2 - 1])
    if len(kx_range) != 2 or any(value != int(value) for value in kx_range):
        raise ValueError('kx_range must contain two integer coordinates.')
    coordinates['kx'] = np.arange(int(kx_range[0]), int(kx_range[1]) + 1)
    if len(coordinates['kx']) != samples:
        raise ValueError('kx_range does not match the STD readout length.')
    grid_shape, crops, processing = [], [], {}
    for direction in ('z', 'y', 'x'):
        name = 'k' + direction
        coordinate = coordinates[name]
        if direction == 'z' and dimensions == 2:
            coordinate = np.array([0], dtype=np.int64)
            coordinates[name] = coordinate
            factor, length = 1.0, 1
        else:
            factor = parameter(name + '_oversample_factor')[0]
            if not np.isfinite(factor) or factor < 1:
                raise ValueError('Oversampling factors must be finite and at least 1.')
            sense = float(parameters.get((0, 0, 0, direction.upper() + '-direction SENSE factor'), [1])[0])
            if sense != 1:
                raise ValueError('SENSE acceleration requires reconstruction not provided by ComputeSNR.')
            minimum = max(1, -2 * int(coordinate.min()), 2 * int(coordinate.max()) + 1)
            resolution = parameter(direction.upper() + '-resolution', [0], True)[0]
            length = int(round(resolution * factor)) if resolution else minimum
            if length < minimum:
                raise ValueError('Header FFT grid does not contain acquired {} coordinates.'.format(name))
        kept = int(round(length / factor)) if remove_oversampling else length
        if kept < 1:
            raise ValueError('Oversampling removal leaves an empty image axis.')
        start = length // 2 - kept // 2
        grid_shape.append(length)
        crops.append(slice(start, start + kept))
        processing[direction] = {'grid_size': length, 'output_size': kept,
                                 'oversampling_factor': factor, 'crop_start': start}

    if use_readout_split:
        length = grid_shape[-1]
        if not np.isclose(processing['x']['oversampling_factor'], 2, rtol=0, atol=1e-8):
            raise ValueError('Odd/even readout SNR requires a 2x frequency-direction oversampling factor.')
        if length % 2:
            raise ValueError(
                'Odd/even readout SNR requires an even FFT grid '
                '(grid={}, acquired={}, kx={}..{}).'.format(
                    length, samples, int(coordinates['kx'][0]), int(coordinates['kx'][-1])))
        processing['x'].update({'acquired_samples': samples,
                                 'acquired_kx_range': [int(coordinates['kx'][0]), int(coordinates['kx'][-1])],
                                 'zero_filled_samples': length - samples})

    lookup = {axis: {value: index for index, value in enumerate(values[axis])}
              for axis in standard_axes[:-1]}
    if use_readout_split:
        lookup['dyn'] = {values['dyn'][0]: 0}
    coverage = np.zeros((coils, dynamics, kz_count, ky_count), dtype=bool)
    header = metadata['header']
    required = ('typ', 'size') + standard_axes[:-1]
    if any(len(header[name]) != len(header['typ']) for name in required):
        raise ValueError('Inconsistent metadata header column lengths.')
    for index, kind in enumerate(header['typ']):
        if kind != 'STD':
            continue
        if any(header[axis][index] not in lookup[axis] for axis in standard_axes[:-1]):
            continue
        if header['size'][index] != samples * 8:
            raise ValueError('Variable STD readout lengths are not supported for SNR propagation.')
        destination = tuple(lookup[axis][header[axis][index]] for axis in retained[:-1])
        if coverage[destination]:
            raise ValueError('Duplicate STD destination in metadata.')
        coverage[destination] = True
    if np.any(coverage.sum(axis=(2, 3)) == 0):
        raise ValueError('Every coil/dynamic must contain acquired STD samples.')
    if use_rf_off:
        if np.any(coverage[:, 0] & ~coverage[:, 1]):
            raise ValueError('RF-off dynamic must cover every acquired signal sample.')
        common = coverage[:, 1].all(axis=0)
        noise_frame = np.array(source[:, 1], dtype=np.complex64, copy=True)
        noise = noise_frame[:, common, :].reshape(coils, -1)
    raw_covariance = None if use_readout_split else estimate_noise_covariance(noise, noise_scale)
    image_covariance = np.empty((dynamics, coils, coils), dtype=np.complex128)
    acquired_counts = []
    for dynamic in range(dynamics):
        mask = coverage[:, dynamic].reshape(coils, -1).astype(np.float64)
        overlap = (mask @ mask.T) * samples
        if not use_readout_split:
            image_covariance[dynamic] = raw_covariance * overlap
        acquired_counts.append(overlap.diagonal().astype(np.int64).tolist())
    image_shape = tuple(processing[axis]['output_size'] for axis in ('z', 'y', 'x'))
    reconstructed_dynamics = 2 if use_readout_split else dynamics
    images = np.empty((coils, reconstructed_dynamics) + image_shape, dtype=np.complex64)
    grid_indices = np.ix_(*(coordinates['k' + axis] + length // 2
                            for axis, length in zip(('z', 'y', 'x'), grid_shape)))
    for coil in range(coils):
        for dynamic in range(dynamics):
            frame = np.array(source[coil, dynamic], dtype=np.complex64, copy=True)
            mask_dynamic = 0 if use_rf_off and dynamic == 1 else dynamic
            frame *= coverage[coil, mask_dynamic, :, :, None]
            grid = np.zeros(grid_shape, dtype=np.complex64)
            grid[grid_indices] = frame
            if use_readout_split:
                images[coil, 0], images[coil, 1] = _reconstruct_readout_pair(grid, crops)
            else:
                grid = np.fft.fftn(np.fft.ifftshift(grid))
                grid = np.fft.fftshift(grid)
                images[coil, dynamic] = grid[tuple(crops)]
    if dimensions == 2:
        images = images[:, :, 0]
    if use_rf_off or use_readout_split:
        measured_covariance = estimate_noise_covariance(images[:, 1].reshape(coils, -1), noise_scale)
        if use_rf_off:
            predicted_std = np.sqrt(image_covariance[0].diagonal().real)
            measured_std = np.sqrt(measured_covariance.diagonal().real)
        image_covariance = measured_covariance[None]
        if not retain_noise:
            images = images[:, :1]
    details = {'axes': ['chan', 'frame' if use_readout_split else 'dyn']
                       + (['z', 'y', 'x'] if dimensions == 3 else ['y', 'x']),
               'coil_ids': list(values['chan']),
               'dynamic_ids': list(values['dyn'][:1] if use_readout_split else values['dyn']),
               'processing': processing,
               'raw_noise_covariance': None if raw_covariance is None else raw_covariance.tolist(),
               'acquired_samples_per_coil_dynamic': np.asarray(acquired_counts).T.tolist(),
               'noise_std_scale': noise_scale, 'remove_oversampling': bool(remove_oversampling),
               'noise_source': ('odd/even readout from dynamic index 0' if use_readout_split
                                else 'RF-off dynamic index 1' if use_rf_off else 'NOI'),
               'noise_sample_count': int(np.prod(images.shape[2:])) if use_readout_split else noise.shape[1],
               'fft': 'centered forward, unnormalized; supplied reader chopping preserved',
               'assumptions': ['User confirms Cartesian acquisition.',
                               'Noise reference and signal have matched gain and bandwidth after noise scaling.',
                               ('Image-noise covariance is pooled across the retained FOV; assumes stationary noise.'
                                if use_rf_off else 'Noise samples are independent across readout/encoding samples.'),
                               'Zero-filled reconstruction only; no SENSE, partial-Fourier recovery or phase correction.',
                               ('Dynamic index 0 is signal; index 1 is RF-off noise.' if use_rf_off
                                else 'Dynamics remain separate; neither is assumed to be noise-only.')]}
    if use_rf_off:
        details.update({'noise_covariance_domain': 'reconstructed RF-off image with signal sampling mask',
                        'image_noise_sample_count': int(np.prod(images.shape[2:])),
                        'measured_to_independent_noise_std_ratio': (measured_std / predicted_std).tolist()})
    if use_readout_split:
        details.update({
            'noise_covariance_domain': 'phase-aligned odd/even half-difference image',
            'image_noise_sample_count': int(np.prod(images.shape[2:])),
            'readout_pair': {'source_dynamic_index': 0, 'subset_intensity_scale': 2,
                             'phase_ramp_corrected': True,
                             'signal': '(even + odd) / 2', 'noise': '(even - odd) / 2'},
            'assumptions': [
                'User confirms Cartesian acquisition; only dynamic index 0 is used.',
                'Object fits within the retained half-FOV along the frequency direction; no aliased signal.',
                'Odd/even readout noise is uncorrelated and has equal variance; receiver filtering can bias SNR.',
                'Phase-aligned interleaves contain the same complex signal.',
                'Image-noise covariance is pooled across the retained FOV; assumes stationary noise.',
                'Zero-filled reconstruction only; no SENSE or partial-Fourier recovery.']})
    return images, image_covariance, details


class ExternalNode(gpi.NodeAPI):
    """Compute covariance-aware SNR and optionally predict Cartesian SENSE g-factor.

    Connect ReadDataList out -> in, Metadata -> Metadata.
    Input is complex raw Cartesian data with one mix/echo/location/average.
    SNR Method defaults to RF-off: exactly two dynamics, index 0 signal and
    index 1 RF-off noise. Both SNR methods derive noise from the main input;
    no separate noise input is needed.
    FFT and optional oversampling removal reconstruct each coil/dynamic.
    RF-off noise is reconstructed with the signal sampling mask and crop;
    its measured image-domain covariance sets SNR, without assuming independent
    raw readout samples. The covariance is pooled across the retained FOV.
    Noise Std Scale calibrates RF-off standard deviation to signal receiver units;
    default 1 assumes identical gain and bandwidth. This cannot be inferred.
    Odd/even readout mode uses dynamic index 0 only, with contiguous 2x
    frequency-direction oversampling. Zero-filling to the reconstruction
    matrix is allowed, and interleaves follow the padded grid's kx parity.
    Both interleaves are phase-ramp aligned
    and scaled to full-reconstruction intensity before forming the complex
    mean (signal) and half-difference (noise). Noise covariance is measured
    from that half-difference. Equal-variance, uncorrelated interleave noise
    and signal confined to the retained half-FOV are required: receiver
    filtering, out-of-FOV signal or inconsistent interleaves can bias SNR.
    Oversampling removal is required in this mode. Later dynamics are ignored.
    coil_snr has (coil, spatial...) axes; combined_snr has spatial axes only.
    rss has two frames: index 0 signal, index 1 RF-off or half-difference noise.
    RSS is unwhitened and is not power-bias corrected or noise-scale adjusted.
    coil_images contains only the complex signal images.
    Outputs rotate the last two spatial axes by positive 90 degrees (NumPy
    convention); 3D outputs also flip z. Coil axes are never transformed.
    Combined SNR is whitened RSS, not an unbiased optimal linear combination.
    Power Bias Correction subtracts expected noise power and clips at zero;
    it reduces magnitude bias but is not an unbiased low-SNR amplitude estimate.
    SNR outputs contain only signal maps, without a dynamic or noise-map axis.
    Predict g-factor optionally models hypothetical uniform Cartesian SENSE
    acceleration of the fully sampled input, not accelerated reconstruction.
    R y/R z refer to native acquisition axes before output rotation; R z must
    be 1 for 2D and image dimensions must be divisible by the chosen factors.
    Sensitivity maps are Gaussian-smoothed complex coil images normalized by
    their RSS. Smoothing is in voxels; the mask is a percentage of peak
    unsmoothed RSS. Accuracy depends on these approximate sensitivity maps.
    Masked-out locations are assumed signal-free. g_factor is NaN outside the
    support mask and inf for singular alias groups (relative rank cutoff 1e-10).
    Covariance Floor is applied to noise covariance only, not SENSE encoding.
    predicted_snr = combined_snr / (g_factor * sqrt(R y * R z)); it inherits
    the measured SNR estimator's bias. This is not a CS/regularized-SENSE model.
    sensitivity_maps, g_factor_mask, g_factor and predicted_snr share the
    existing output orientation. Prediction is disabled by default. If the
    requested prediction is invalid, SNR outputs remain available and the
    prediction outputs are cleared; SNR Info and metadata explain the reason.
    """

    def execType(self):
        return gpi.GPI_PROCESS

    def initUI(self):
        self.addWidget('TextBox', 'SNR Info:')
        self.addWidget('ExclusivePushButtons', 'Acquisition',
                       buttons=['Cartesian', 'Non-Cartesian'], val=0)
        self.addWidget('ExclusivePushButtons', 'SNR Method',
                   buttons=['RF-off dynamic', 'Odd/even readout'], val=0)
        self.addWidget('PushButton', 'Remove Oversampling', toggle=True, val=True)
        self.addWidget('PushButton', 'Power Bias Correction', toggle=True, val=True)
        self.addWidget('DoubleSpinBox', 'Noise Std Scale', min=0.000001, max=1000000.0, val=1.0)
        self.addWidget('DoubleSpinBox', 'Covariance Floor', min=0.00000001,
                       max=0.1, decimals=8, val=0.000001)
        self.addWidget('PushButton', 'Predict g-factor', toggle=True, val=False)
        self.addWidget('SpinBox', 'g-factor R y', min=1, max=32, val=2, visible=False)
        self.addWidget('SpinBox', 'g-factor R z', min=1, max=32, val=1, visible=False)
        self.addWidget('DoubleSpinBox', 'Sensitivity Smoothing (voxels)',
                   min=0., max=50., val=2., visible=False)
        self.addWidget('DoubleSpinBox', 'Sensitivity Mask (%)',
                   min=0., max=99., val=5., visible=False)
        self.addWidget('PushButton', 'Compute', toggle=True, val=False)
        self.addInPort('in', 'NPYarray', obligation=gpi.REQUIRED)
        self.addInPort('Metadata', 'DICT', obligation=gpi.REQUIRED)
        for title in ('coil_snr', 'combined_snr', 'coil_images', 'rss', 'noise_covariance',
                  'g_factor', 'predicted_snr', 'sensitivity_maps', 'g_factor_mask'):
            self.addOutPort(title, 'NPYarray')
        self.addOutPort('SNR Metadata', 'DICT')

    def validate(self):
        split = self.getVal('SNR Method') == 1
        self.setAttr('Remove Oversampling', visible=not split)
        if split:
            self.setAttr('Remove Oversampling', val=True)
        predict = bool(self.getVal('Predict g-factor'))
        for title in ('g-factor R y', 'g-factor R z', 'Sensitivity Smoothing (voxels)',
                      'Sensitivity Mask (%)'):
            self.setAttr(title, visible=predict)
        return 0

    def compute(self):
        for title in ('coil_snr', 'combined_snr', 'coil_images', 'rss',
                      'noise_covariance', 'SNR Metadata', 'g_factor',
                      'predicted_snr', 'sensitivity_maps', 'g_factor_mask'):
            self.setData(title, None)
        if not self.getVal('Compute'):
            return 0
        try:
            if self.getVal('Acquisition') != 0:
                raise ValueError('Non-Cartesian data require trajectory-aware reconstruction first.')
            split = self.getVal('SNR Method') == 1
            images, covariance, details = reconstruct_cartesian(
                self.getData('in'), None, self.getData('Metadata'),
                remove_oversampling=self.getVal('Remove Oversampling'),
                noise_scale=self.getVal('Noise Std Scale'), use_rf_off=not split,
                retain_noise=True, use_readout_split=split)
            covariance = covariance[:1]
            g_factor = sensitivity_maps = g_factor_mask = predicted_snr = None
            prediction = {'enabled': bool(self.getVal('Predict g-factor')), 'available': False}
            if prediction['enabled']:
                acceleration_y = self.getVal('g-factor R y')
                acceleration_z = self.getVal('g-factor R z')
                smoothing = self.getVal('Sensitivity Smoothing (voxels)')
                mask_fraction = self.getVal('Sensitivity Mask (%)') / 100.
                prediction.update({'native_acceleration_y': acceleration_y,
                                   'native_acceleration_z': acceleration_z,
                                   'native_spatial_shape': list(images.shape[2:])})
                try:
                    _g_factor_dimensions(images.shape[2:], acceleration_y, acceleration_z)
                    sensitivity_maps, g_factor_mask = estimate_sensitivity_maps(
                        images[:, 0], smoothing=smoothing, mask_fraction=mask_fraction)
                    g_factor = calculate_g_factor(
                        sensitivity_maps, covariance[0], acceleration_y, acceleration_z,
                        support=g_factor_mask, covariance_floor=self.getVal('Covariance Floor'))
                    acceleration = acceleration_y * acceleration_z
                    prediction.update({
                        'available': True,
                        'model': 'uniform Cartesian unregularized SENSE',
                        'total_acceleration': acceleration,
                        'sensitivity_estimation': 'Gaussian-smoothed complex coil images / RSS',
                        'smoothing_voxels': smoothing, 'mask_fraction_of_peak_rss': mask_fraction,
                        'support_voxels': int(g_factor_mask.sum()),
                        'singular_voxels': int(np.isinf(g_factor).sum()),
                        'rank_relative_cutoff': 1e-10,
                        'outside_support': 'NaN; masked locations assumed signal-free',
                        'predicted_snr_formula': 'combined_snr / (g_factor * sqrt(total_acceleration))',
                        'limitations': 'Approximate sensitivities; no CS, regularization or CAIPI model.'})
                except (ValueError, TypeError, MemoryError, np.linalg.LinAlgError) as error:
                    g_factor = sensitivity_maps = g_factor_mask = None
                    prediction['reason'] = str(error)
                    self.log.warn('ComputeSNR: g-factor prediction unavailable; SNR retained: {}'.format(error))
            flip_z = images.ndim == 5
            if flip_z:
                images = np.flip(images, axis=-3)
            images = np.rot90(images, k=1, axes=(-2, -1))
            if prediction['available']:
                if flip_z:
                    sensitivity_maps = np.flip(sensitivity_maps, axis=-3)
                    g_factor = np.flip(g_factor, axis=-3)
                    g_factor_mask = np.flip(g_factor_mask, axis=-3)
                sensitivity_maps = np.rot90(sensitivity_maps, axes=(-2, -1))
                g_factor = np.rot90(g_factor, axes=(-2, -1))
                g_factor_mask = np.rot90(g_factor_mask, axes=(-2, -1))
            result = calculate_snr(images[:, :1], covariance,
                                   bias_correction=self.getVal('Power Bias Correction'),
                                   covariance_floor=self.getVal('Covariance Floor'))
            if prediction['available']:
                predicted_snr = np.full(g_factor.shape, np.nan, dtype=np.float32)
                np.divide(result['combined_snr'][0], g_factor * np.sqrt(acceleration),
                          out=predicted_snr, where=g_factor_mask)
            noise_power = np.zeros(images.shape[2:], dtype=np.float64)
            for noise_image in images[:, 1]:
                noise_power += (noise_image.real.astype(np.float64) ** 2
                                + noise_image.imag.astype(np.float64) ** 2)
            rss = np.stack((result['rss'][0], np.sqrt(noise_power).astype(np.float32)))
            details.update({'image_shape': list(images[:, 0].shape),
                            'source_axes': details['axes'],
                            'axes': [axis for axis in details['axes'] if axis not in ('dyn', 'frame')],
                            'snr_method': 'odd/even readout' if split else 'RF-off dynamic',
                            'signal_frame_index': 0, 'noise_frame_index': 1,
                            'signal_dynamic_index': 0, 'noise_dynamic_index': None if split else 1,
                            'signal_dynamic_id': details['dynamic_ids'][0],
                            'noise_dynamic_id': None if split else details['dynamic_ids'][1],
                            'orientation': {'flip_z': flip_z, 'rotate90_k': 1,
                                            'rotate90_axes': [-2, -1]},
                            'power_bias_correction': bool(self.getVal('Power Bias Correction')),
                            'covariance_floor': self.getVal('Covariance Floor'),
                            'covariance_details': result['covariance_details'],
                            'g_factor_prediction': prediction})
            details['axes'][-2:] = details['axes'][-2:][::-1]
            details['combined_axes'] = details['axes'][1:]
            details['rss_axes'] = ['frame' if split else 'dyn'] + details['combined_axes']
            details['rss_shape'] = list(rss.shape)
            details['rss_dynamic_labels'] = ['signal', 'odd/even half-difference noise' if split else 'RF-off noise']
        except (ValueError, KeyError, TypeError, IndexError, MemoryError, np.linalg.LinAlgError) as error:
            self.log.error('ComputeSNR: {}'.format(error))
            self.setAttr('SNR Info:', val='Cannot compute SNR:\n{}'.format(error))
            return 1
        self.setData('coil_snr', result['coil_snr'][:, 0])
        self.setData('combined_snr', result['combined_snr'][0])
        self.setData('rss', rss)
        self.setData('coil_images', images[:, 0])
        self.setData('noise_covariance', covariance[0])
        self.setData('g_factor', g_factor)
        self.setData('predicted_snr', predicted_snr)
        self.setData('sensitivity_maps', sensitivity_maps)
        self.setData('g_factor_mask', g_factor_mask)
        self.setData('SNR Metadata', details)
        if split:
            noise_info = (
                'Dynamic 0: phase-aligned odd/even mean; noise: half-difference.\n'
                'Assumes equal, uncorrelated interleave noise and no out-of-FOV signal.\n'
                'Receiver filtering or signal leakage can bias SNR.')
            self.log.warn('ComputeSNR: {}'.format(noise_info))
        else:
            noise_info = ('Signal: dynamic 0; noise: RF-off dynamic 1.\n'
                          'Assumes matching signal/RF-off gain and bandwidth after scaling.')
        prediction_info = ''
        if prediction['available']:
            prediction_info = (
                '\nPredicted SENSE g-factor: native R y={}, R z={}; '
                '{} support voxels, {} singular.\n'
                'Estimated sensitivities; masked locations assumed signal-free; '
                'NaN outside support, inf for singular encoding.').format(
                    acceleration_y, acceleration_z, prediction['support_voxels'],
                    prediction['singular_voxels'])
        elif prediction['enabled']:
            prediction_info = '\ng-factor prediction unavailable (SNR retained):\n' + prediction['reason']
        self.setAttr('SNR Info:', val=(
            'coil images/SNR: {}\ncombined SNR: {}\naxes: {}\n'
            '{}\nNoise Std Scale: {}\n'
            'Zero-filled Cartesian reconstruction.{}').format(
                list(images[:, 0].shape), list(result['combined_snr'][0].shape),
                ', '.join(details['axes']), noise_info, details['noise_std_scale'],
                prediction_info))
        return 0