"""Temporal SNR of repeated Cartesian acquisitions with noise-aware coil combination."""

import gpi
import numpy as np
from scipy import fft

from gpi_core.fileIO.GPI.ComputeSNR_GPI import calculate_snr, estimate_noise_covariance


def calculate_tsnr(raw, noise, remove_oversampling=True, noise_scale=1.0,
                   covariance_floor=1e-6):
    """Reconstruct (coil, repetition, [z,] y, x), then measure magnitude tSNR.

    Noise is complex (coil, samples...) with matching coil order, receiver gain,
    bandwidth and filtering. The fully sampled centered Cartesian FFT is unitary,
    so raw and reconstructed per-component noise covariance have the same scale.
    Cropping assumes exactly 2x readout oversampling when requested.
    """
    raw = np.asarray(raw)
    noise = np.asarray(noise)
    if raw.ndim not in (4, 5) or not np.iscomplexobj(raw):
        raise ValueError('Input must be complex (coil, repetition, [z,] y, x) k-space.')
    if any(size < 1 for size in raw.shape) or raw.shape[1] < 2:
        raise ValueError('At least two repetitions and nonempty coil/spatial axes are required.')
    if noise.ndim < 2 or noise.shape[0] != raw.shape[0]:
        raise ValueError('Noise must have matching coils on axis 0, followed by noise samples.')
    if remove_oversampling and raw.shape[-1] % 2:
        raise ValueError('Removing 2x readout oversampling requires an even x size.')
    covariance = estimate_noise_covariance(noise.reshape(raw.shape[0], -1), noise_scale)
    spatial_axes = tuple(range(1, raw.ndim - 1))
    combined = None
    for repetition in range(raw.shape[1]):
        frame = raw[:, repetition]
        if not np.isfinite(frame).all():
            raise ValueError('K-space must contain only finite values.')
        image = fft.fftshift(fft.fftn(fft.ifftshift(frame, axes=spatial_axes),
                                    axes=spatial_axes, norm='ortho'), axes=spatial_axes)
        if remove_oversampling:
            width = image.shape[-1] // 2
            start = (image.shape[-1] - width) // 2
            image = image[..., start:start + width]
        result = calculate_snr(image[:, None], covariance[None], bias_correction=False,
                               covariance_floor=covariance_floor)
        magnitude = np.rot90(result['combined_snr'][0], axes=(-2, -1))
        if raw.ndim == 5:
            magnitude = np.flip(magnitude, axis=0)
        if combined is None:
            combined = np.empty((raw.shape[1],) + magnitude.shape, dtype=np.float32)
        combined[repetition] = magnitude
    mean = combined.mean(axis=0, dtype=np.float64)
    std = combined.std(axis=0, ddof=1, dtype=np.float64)
    tsnr = np.full(mean.shape, np.nan, dtype=np.float32)
    np.divide(mean, std, out=tsnr, where=std > 0)
    return {'combined_images': combined, 'temporal_mean': mean.astype(np.float32),
            'temporal_std': std.astype(np.float32), 'tSNR': tsnr,
            'noise_covariance': covariance}


class ExternalNode(gpi.NodeAPI):
    """Compute temporal SNR from repeated, fully sampled Cartesian k-space.

    Connect complex in (coil, repetition, [z,] y, x) and separate complex
    noise (coil, samples...). For [32, 50, 240, 480], axis 1 holds all 50
    repetitions. Noise must be noise-only, with matching coil order and receiver
    conditions; Noise Std Scale calibrates its standard deviation if needed.
    No Metadata input is required. No repetition is assumed noise-only.

    Reconstruction uses a centered forward orthonormal FFT, followed by optional
    central cropping of exactly 2x readout oversampling (x only). Enable cropping
    only when the acquisition really has 2x readout oversampling. Spatial outputs
    follow ComputeSNR: positive 90-degree rotation of y/x, plus z flip for 3D.
    No SENSE, partial-Fourier recovery, gridding or motion correction is performed.
    Zero-filled or filtered data can violate the stationary noise assumption.

    Each repetition uses the same measured covariance and covariance-whitened
    RSS combination as ComputeSNR, with power-bias correction disabled. These
    are magnitude images in receiver-noise standard-deviation units, not an
    optimal complex linear coil combination. tSNR is temporal mean / sample
    standard deviation (ddof=1) of this combined magnitude series. It measures
    all temporal fluctuations, including drift, motion and physiological noise,
    not just receiver noise. No detrending, frame rejection or bias correction
    is applied. Zero temporal variance gives NaN, including signal-free zeros.
    """

    def execType(self):
        return gpi.GPI_PROCESS

    def initUI(self):
        self.addWidget('TextBox', 'tSNR Info:')
        self.addWidget('PushButton', 'Remove Oversampling', toggle=True, val=True)
        self.addWidget('DoubleSpinBox', 'Noise Std Scale', min=0.000001,
                       max=1000000.0, val=1.0)
        self.addWidget('DoubleSpinBox', 'Covariance Floor', min=0.00000001,
                       max=0.1, decimals=8, val=0.000001)
        self.addWidget('PushButton', 'Compute', toggle=True, val=False)
        self.addInPort('in', 'NPYarray', obligation=gpi.REQUIRED)
        self.addInPort('noise', 'NPYarray', obligation=gpi.REQUIRED)
        for title in ('tSNR', 'temporal_mean', 'temporal_std', 'combined_images',
                      'noise_covariance'):
            self.addOutPort(title, 'NPYarray')
        self.addOutPort('tSNR Metadata', 'DICT')

    def validate(self):
        return 0

    def compute(self):
        if not self.getVal('Compute'):
            return 0
        try:
            raw = self.getData('in')
            noise = self.getData('noise')
            remove_oversampling = bool(self.getVal('Remove Oversampling'))
            noise_scale = self.getVal('Noise Std Scale')
            floor = self.getVal('Covariance Floor')
            outputs = calculate_tsnr(raw, noise, remove_oversampling, noise_scale, floor)
            axes = ['repetition'] + (['z', 'y', 'x'] if raw.ndim == 5 else ['y', 'x'])
            details = {
                'input_shape': list(raw.shape), 'input_axes': ['coil'] + axes,
                'combined_axes': axes, 'map_axes': axes[1:],
                'repetitions': int(raw.shape[1]),
                'noise_sample_count': int(np.prod(noise.shape[1:])),
                'noise_std_scale': noise_scale, 'covariance_floor': floor,
                'noise_covariance_domain': 'raw per-component; unchanged by unitary FFT',
                'remove_2x_readout_oversampling': remove_oversampling,
                'fft': 'centered forward, orthonormal, spatial axes only',
                'orientation': 'rot90 y/x; additionally flip z for 3D',
                'coil_combination': 'fixed noise-covariance-whitened RSS magnitude',
                'formula': 'temporal mean / temporal sample standard deviation',
                'standard_deviation_ddof': 1, 'zero_variance': 'NaN',
                'detrending': False, 'power_bias_correction': False,
                'assumptions': ['Fully sampled Cartesian k-space, same sampling each repetition.',
                                'Noise-only reference has matched coil order, gain and bandwidth.',
                                'Noise covariance is stationary across time and space.']}
        except (ValueError, TypeError, MemoryError, np.linalg.LinAlgError) as error:
            for title in ('tSNR', 'temporal_mean', 'temporal_std', 'combined_images',
                          'noise_covariance', 'tSNR Metadata'):
                self.setData(title, None)
            self.setAttr('tSNR Info:', val=str(error))
            self.log.warn('ComputeTSNR: {}'.format(error))
            return 1
        for title, data in outputs.items():
            self.setData(title, data)
        self.setData('tSNR Metadata', details)
        self.setAttr('tSNR Info:', val=(
            '{} repetitions; combined images: {}\n'
            'tSNR = temporal mean / sample std (ddof=1).\n'
            'Fixed noise-whitened RSS; no detrending or power-bias correction.').format(
                raw.shape[1], list(outputs['combined_images'].shape)))
        return 0