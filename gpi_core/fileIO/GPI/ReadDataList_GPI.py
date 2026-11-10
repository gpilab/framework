"""Philips list/data reader adapted from readPhilipsExports_listData.

Original reader contributors: Nick Zwart, Daniel Borup, and Ryan Robison,
BNI/Mayo MRTUD team (PI: Jim Pipe).
"""

from pathlib import Path

import gpi
import numpy as np


COLUMNS = ('typ mix dyn card echo loca chan extr1 extr2 ky kz '
           'n.a. aver sign rf grad enc rtop rr size offset').split()
DATA_AXES = ('chan', 'mix', 'dyn', 'card', 'extr1', 'extr2', 'echo',
             'aver', 'loca', 'kz', 'ky')
TYPE_AXES = {
    'STD': DATA_AXES,
    'NOI': ('chan',),
    'PHC': DATA_AXES[:-1] + ('rf', 'grad'),
    'PHX': ('chan', 'mix', 'echo', 'loca', 'rf', 'grad', 'sign'),
}
OUTPUTS = (('out', 'STD'), ('noise', 'NOI'), ('phase', 'PHC'), ('phase_extra', 'PHX'))


def resolve_pair(filename):
    path = Path(filename).expanduser()
    if path.suffix.lower() not in ('.list', '.data'):
        raise ValueError('Select a Philips .list or .data file.')
    if not path.is_file():
        raise ValueError('File not found: {}'.format(path))
    companions = {}
    for candidate in path.parent.iterdir():
        if (candidate.is_file() and candidate.stem == path.stem
                and candidate.suffix.lower() in ('.list', '.data')):
            suffix = candidate.suffix.lower()
            if suffix in companions:
                raise ValueError('More than one companion found for {}.'.format(suffix))
            companions[suffix] = candidate
    if len(companions) != 2:
        raise ValueError('Both .list and .data files with the same base name are required.')
    return companions['.list'], companions['.data']


def read_list(filename):
    text = Path(filename).read_text(encoding='utf-8-sig')
    records = []
    for line_number, line in enumerate(text.splitlines(), 1):
        fields = line.split()
        if not fields or fields[0] in ('#', '.') or not fields[0].isalpha():
            continue
        if not fields[0].isupper():
            continue
        if len(fields) != len(COLUMNS):
            if fields[0] in TYPE_AXES:
                raise ValueError('Invalid data record at list line {}.'.format(line_number))
            continue
        record = dict(zip(COLUMNS, fields))
        try:
            record.update({name: int(record[name]) for name in COLUMNS[1:]})
        except ValueError as error:
            raise ValueError('Invalid integer at list line {}.'.format(line_number)) from error
        records.append(record)
    if not records:
        raise ValueError('No data records found in the list file.')
    return records, text


def read_philips(filename, coil=-1, location=-1, chop_ky=False,
                 squeeze=True, propeller='None', chop_kz=False):
    """Return acquisition-domain complex64 arrays and metadata without FFT/cropping.

    STD uses the original reader's MPF loop order. Other record types have
    independent channel and sample counts. Short readouts are zero-padded.
    Duplicate destination indices raise rather than silently overwrite data.
    The API defaults to unchanged samples; the node UI enables ky/kz chopping.
    """
    list_path, data_path = resolve_pair(filename)
    records, text = read_list(list_path)
    selected = [record for record in records
                if (coil == -1 or record['chan'] == coil)
                and (location == -1 or record['typ'] == 'NOI' or record['loca'] == location)]
    if not any(record['typ'] == 'STD' for record in selected):
        raise ValueError('No STD records match the selected coil/location.')
    if propeller not in ('None', 'TSE', 'GRASE'):
        raise ValueError('Unknown Propeller mode: {}.'.format(propeller))
    outputs = {}
    descriptions = {}
    file_size = data_path.stat().st_size
    with data_path.open('rb') as stream:
        for kind, type_axes in TYPE_AXES.items():
            group = [record for record in selected if record['typ'] == kind]
            if not group:
                outputs[kind] = None
                descriptions[kind] = None
                continue
            axes = list(type_axes)
            values = {axis: sorted({record[axis] for record in group}) for axis in axes}
            lookup = {axis: {value: index for index, value in enumerate(values[axis])}
                      for axis in axes}
            for record in group:
                size, offset = record['size'], record['offset']
                if size <= 0 or size % 8 or offset < 0 or offset + size > file_size:
                    raise ValueError('Invalid size/offset or truncated data for {} '
                                     'at byte {}.'.format(kind, offset))
            samples = max(record['size'] // 8 for record in group)
            shape = tuple(len(values[axis]) for axis in axes) + (samples,)
            output = np.zeros(shape, dtype=np.complex64)
            occupied = set()
            for record in group:
                destination = tuple(lookup[axis][record[axis]] for axis in axes)
                if destination in occupied:
                    raise ValueError('Duplicate {} destination indices: {}.'.format(
                        kind, destination))
                occupied.add(destination)
                stream.seek(record['offset'])
                count = record['size'] // 8
                readout = np.fromfile(stream, dtype='<c8', count=count)
                if readout.size != count:
                    raise ValueError('Data file ended while reading {}.'.format(kind))
                if kind == 'STD' and chop_ky and record['ky'] % 2 == 0:
                    readout *= -1
                if (kind == 'STD' and chop_kz and len(values['kz']) > 1
                        and record['kz'] % 2 == 0):
                    readout *= -1
                output[destination + (slice(0, count),)] = readout
            axes.append('samp')
            if kind == 'STD' and propeller != 'None':
                rf_count = len({record['rf'] for record in group})
                grad_count = len({record['grad'] for record in group})
                if propeller == 'TSE' and grad_count == len(values['echo']):
                    grad_count = 1
                if rf_count > 1:
                    lines_per_shot = rf_count * grad_count
                    ky_count = len(values['ky'])
                    if ky_count % lines_per_shot:
                        raise ValueError('Propeller ky count is not divisible by rf*grad.')
                    shots = ky_count // lines_per_shot
                    output = output.reshape(output.shape[:-2] +
                                            (lines_per_shot, shots, samples))
                    output = output.swapaxes(-3, -2)
                    axes[-2:-1] = ['shots', 'rf*grad']
                    values['shots'] = list(range(shots))
                    values['rf*grad'] = list(range(lines_per_shot))
            full_shape = list(output.shape)
            if squeeze:
                axes = [axis for axis, size in zip(axes, output.shape) if size != 1]
                output = output.squeeze()
            outputs[kind] = output
            descriptions[kind] = {'axes': axes, 'shape': list(output.shape),
                                  'unsqueezed_shape': full_shape,
                                  'index_values': values, 'dtype': str(output.dtype),
                                  'record_count': len(group)}
    metadata = {'list_file': str(list_path), 'data_file': str(data_path),
                'coil': coil, 'location': location, 'chop_ky': bool(chop_ky),
                'chop_kz': bool(chop_kz),
                'squeeze': bool(squeeze), 'propeller': propeller,
                'outputs': descriptions, 'list_text': text,
                'ignored_types': sorted({record['typ'] for record in records} - TYPE_AXES.keys()),
                'header': {name: [record[name] for record in records] for name in COLUMNS}}
    return outputs, metadata


class ExternalNode(gpi.NodeAPI):
    """Read Philips .list/.data exports, not PAR/REC or XML/REC images.

    Select either file. Coil and Location use acquisition IDs; -1 reads all.
    out, noise, phase and phase_extra are complex64 STD, NOI, PHC and PHX
    respectively. Absent auxiliary data gives None. Metadata contains the
    original list text, table, axes and index values. Other vector types are
    listed in ignored_types, not reconstructed or applied as corrections.
    STD order: chan, mix, dyn, card, extr1, extr2, echo, aver, loca, kz, ky,
    samp. Squeeze removes singleton axes with matching metadata labels.
    Chop ky and Chop kz default to enabled and negate even ky/kz STD lines.
    Chop kz applies only when multiple kz indices are present (3D data).
    Propeller follows the original reader's rf*grad/shot reshape convention
    and defaults to None.
    No FFT, oversampling removal, trajectory inference, phase correction or coil
    combination is performed. Acquisition samples and header text, including
    oversampling factors, remain available for downstream reconstruction/SNR.
    Sparse ky/kz indices are packed in sorted order and retained in metadata.
    Noise and phase outputs remain raw. Disable chopping for unchanged STD samples.
    """

    def execType(self):
        return gpi.GPI_PROCESS

    def initUI(self):
        self.addWidget('TextBox', 'I/O Info:')
        self.addWidget('OpenFileBrowser', 'File Browser', button_title='Browse',
                       caption='Open Philips list/data',
                       filter='Philips list/data (*.list *.data *.LIST *.DATA);;All files (*)')
        self.addWidget('SpinBox', 'Coil', min=-1, max=gpi.GPI_INT_MAX, val=-1)
        self.addWidget('SpinBox', 'Location', min=-1, max=gpi.GPI_INT_MAX, val=-1)
        self.addWidget('PushButton', 'Chop ky', toggle=True, val=True)
        self.addWidget('PushButton', 'Chop kz', toggle=True, val=True)
        self.addWidget('ExclusivePushButtons', 'Propeller',
                       buttons=['None', 'TSE', 'GRASE'], val=0)
        self.addWidget('PushButton', 'Squeeze', toggle=True, val=True)
        self.addWidget('PushButton', 'Read', toggle=True, val=False)
        for title, _ in OUTPUTS:
            self.addOutPort(title, 'NPYarray')
        self.addOutPort('Metadata', 'DICT')
        self.URI = gpi.TranslateFileURI

    def validate(self):
        self.setDetailLabel(self.URI(self.getVal('File Browser')))
        return 0

    def compute(self):
        for title in [title for title, _ in OUTPUTS] + ['Metadata']:
            self.setData(title, None)
        if not self.getVal('Read'):
            return 0
        filename = self.URI(self.getVal('File Browser'))
        try:
            outputs, metadata = read_philips(
                filename, coil=self.getVal('Coil'), location=self.getVal('Location'),
                chop_ky=self.getVal('Chop ky'), squeeze=self.getVal('Squeeze'),
                propeller=('None', 'TSE', 'GRASE')[self.getVal('Propeller')],
                chop_kz=self.getVal('Chop kz'))
        except (OSError, ValueError, MemoryError) as error:
            message = 'Failed to read file:\n{}\n\n{}'.format(filename, error)
            self.log.error('ReadDataList: {}'.format(message))
            self.setAttr('I/O Info:', val=message)
            return 1
        info = [str(filename)]
        for title, kind in OUTPUTS:
            self.setData(title, outputs[kind])
            description = metadata['outputs'][kind]
            if description is not None:
                info.append('{}: {} {}\naxes: {}'.format(
                    title, description['shape'], description['dtype'],
                    ', '.join(description['axes'])))
        if metadata['ignored_types']:
            info.append('Not loaded: ' + ', '.join(metadata['ignored_types']))
        self.setData('Metadata', metadata)
        self.setAttr('I/O Info:', val='\n'.join(info))
        return 0