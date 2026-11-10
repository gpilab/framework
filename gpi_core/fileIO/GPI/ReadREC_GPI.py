from pathlib import Path
import xml.etree.ElementTree as ET

import gpi
import numpy as np


def resolve_rec_pair(filename):
    path = Path(filename)
    suffix = path.suffix.lower()
    if suffix not in ('.xml', '.par', '.rec'):
        raise ValueError('Select a PRIDE XML/REC or Philips PAR/REC file.')
    if not path.is_file():
        raise ValueError('Selected file does not exist: {}.'.format(path))
    companions = {}
    for candidate in path.parent.iterdir():
        extension = candidate.suffix.lower()
        if candidate.is_file() and candidate.stem.casefold() == path.stem.casefold() and extension in ('.xml', '.par', '.rec'):
            if extension in companions:
                raise ValueError('Ambiguous {} companion files.'.format(extension))
            companions[extension] = candidate
    header = companions.get('.xml', companions.get('.par')) if suffix == '.rec' else path
    rec = companions.get('.rec')
    if header is None or rec is None:
        raise ValueError('Both XML and REC files, or PAR and REC files, with the same base name are required.')
    return header, rec


def read_xml_records(filename):
    root = ET.parse(filename).getroot()
    if root.tag != 'PRIDE_V5':
        raise ValueError('Only PRIDE_V5 XML/REC images are supported.')
    images = root.findall('./Image_Array/Image_Info')
    if not images:
        raise ValueError('No Image_Info entries found in the XML.')

    records = []
    for image in images:
        attrs = {attr.attrib['Name']: attr.text
                 for attr in image.findall('Attribute')}
        key = {attr.attrib['Name']: attr.text
               for attr in image.findall('./Key/Attribute')}
        try:
            width = int(attrs['Resolution X'])
            height = int(attrs['Resolution Y'])
            bits = int(attrs['Pixel Size'])
            representation = int(attrs['Pixel Representation'])
            index = int(key['Index'])
            order = (
                key.get('Label Type', ''),
                *(int(key.get(name, '0')) for name in (
                    'Grad Orient', 'BValue', 'Dynamic', 'Phase', 'Echo')),
                key.get('Type', ''), key.get('Sequence', ''),
                int(key['Slice']),
            )
            slope = float(attrs['Rescale Slope'])
            intercept = float(attrs['Rescale Intercept'])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError('Missing or invalid image attributes: {}'.format(error)) from error
        if representation not in (0, 1) or bits not in (8, 16):
            raise ValueError('Only signed/unsigned 8-bit and 16-bit REC pixels are supported.')
        dtype = np.dtype('<{}{}'.format('i' if representation else 'u', bits // 8))
        records.append((order, index, height, width, dtype, slope, intercept))
    return records


def read_par_records(filename):
    from nibabel.parrec import PARRECError, parse_PAR_header

    try:
        with Path(filename).open(encoding='utf-8-sig') as stream:
            _, images = parse_PAR_header(stream)
    except (PARRECError, ValueError, KeyError, IndexError) as error:
        raise ValueError('Invalid or unsupported PAR header: {}.'.format(error)) from error
    if not len(images):
        raise ValueError('No images found in the PAR header.')
    records = []
    for image in images:
        width, height = (int(value) for value in image['recon resolution'])
        bits = int(image['image pixel size'])
        if bits not in (8, 16):
            raise ValueError('Only unsigned 8-bit and 16-bit PAR/REC pixels are supported.')
        order = tuple(int(image[name]) if name in images.dtype.names else 0 for name in (
            'label type', 'gradient orientation number', 'diffusion b value number',
            'dynamic scan number', 'cardiac phase number', 'echo number',
            'image_type_mr', 'scanning sequence', 'slice number'))
        records.append((order, int(image['index in REC file']), height, width,
                        np.dtype('<u{}'.format(bits // 8)),
                        float(image['rescale slope']), float(image['rescale intercept'])))
    return records


def read_rec(filename):
    """Read PRIDE_V5 XML/REC or Philips V4/V4.1/V4.2 PAR/REC images.

    Output is (..., slice, row, column), with varying acquisition keys first:
    label, gradient, b-value, dynamic, phase, echo, type, sequence. Singleton
    acquisition axes are omitted; slices are sorted by number. REC offsets
    come from each image's zero-based index, not header order. Values use
    display scaling (stored * Rescale Slope + Intercept), not floating-point
    scaling. No anatomical reorientation is applied. Selecting REC prefers
    XML when both XML and PAR companions exist; select PAR to override.
    """
    header_path, rec_path = resolve_rec_pair(filename)
    records = (read_par_records(header_path) if header_path.suffix.lower() == '.par'
               else read_xml_records(header_path))
    for _, index, height, width, _, slope, intercept in records:
        if width <= 0 or height <= 0 or index < 0:
            raise ValueError('Image dimensions must be positive and Index nonnegative.')
        if not np.isfinite(slope) or not np.isfinite(intercept):
            raise ValueError('Rescale Slope and Rescale Intercept must be finite.')

    _, _, height, width, dtype, _, _ = records[0]
    if any(record[2:5] != (height, width, dtype) for record in records):
        raise ValueError('All images must have the same dimensions and pixel storage type.')
    indices = [record[1] for record in records]
    if sorted(indices) != list(range(len(records))):
        raise ValueError('REC image indices must be unique and contiguous starting at zero.')
    orders = [record[0] for record in records]
    acquisition_shape = tuple(len({order[axis] for order in orders})
                              for axis in range(len(orders[0])))
    if len(set(orders)) != len(records) or np.prod(acquisition_shape) != len(records):
        raise ValueError('Acquisition keys and slices must form a complete grid without duplicates.')
    output_shape = tuple(size for size in acquisition_shape[:-1] if size > 1)
    output_shape += (acquisition_shape[-1], height, width)
    frame_bytes = height * width * dtype.itemsize
    expected_bytes = len(records) * frame_bytes
    if rec_path.stat().st_size != expected_bytes:
        raise ValueError('REC size does not match {}: expected {} bytes, found {}.'.format(
            header_path.suffix.upper()[1:], expected_bytes, rec_path.stat().st_size))

    out = np.empty((len(records), height, width), dtype=np.float32)
    with rec_path.open('rb') as stream:
        for destination, (_, index, _, _, _, slope, intercept) in enumerate(sorted(records)):
            stream.seek(index * frame_bytes)
            pixels = np.fromfile(stream, dtype=dtype, count=height * width)
            if pixels.size != height * width:
                raise ValueError('REC file ended while reading image {}.'.format(index))
            frame = out[destination]
            frame[:] = pixels.reshape(height, width)
            frame *= np.float32(slope)
            frame += np.float32(intercept)
    return out.reshape(output_shape)


class ExternalNode(gpi.NodeAPI):
    """Read PRIDE_V5 XML/REC or Philips PAR/REC for connection to ImageDisplay.

    Select either file; its same-name companion must be in the same folder.
    out: float32 (..., slice, row, column), with varying acquisition axes first.
    Acquisition order: label, gradient, b-value, dynamic, phase, echo, type,
    sequence; singleton acquisition axes are omitted.
    Values use RecViewer display scaling: stored * Rescale Slope + Intercept.
    PAR versions V4, V4.1 and V4.2 are supported. Selecting REC prefers XML
    if both companion headers exist; select PAR explicitly to use it instead.
    Squeeze is enabled by default and removes all singleton output dimensions
    after the slice flip. Disable it to retain the reader's native shape.
    """

    def execType(self):
        return gpi.GPI_PROCESS

    def initUI(self):
        self.addWidget('TextBox', 'I/O Info:')
        self.addWidget('OpenFileBrowser', 'File Browser',
                       button_title='Browse', caption='Open PAR/XML/REC File',
                       filter='Philips PAR/XML/REC (*.par *.xml *.rec *.PAR *.XML *.REC);;All files (*)')
        self.addWidget('PushButton', 'Squeeze', toggle=True, val=True)
        self.addWidget('PushButton', 'Read', toggle=True, val=0)
        self.addOutPort(title='out', type='NPYarray')
        self.URI = gpi.TranslateFileURI

    def validate(self):
        self.setDetailLabel(self.URI(self.getVal('File Browser')))
        return 0

    def compute(self):
        self.setData('out', None)
        if not self.getVal('Read'):
            return 0
        filename = self.URI(self.getVal('File Browser'))
        try:
            out = read_rec(filename)
        except (OSError, ValueError, ET.ParseError) as error:
            self.log.error('ReadREC: failed to read {}: {}'.format(filename, error))
            self.setAttr('I/O Info:', val='Failed to read file:\n{}\n\n{}'.format(
                filename, error))
            return 1
        
        out = np.flip(out, axis=-3)
        if self.getVal('Squeeze'):
            out = np.squeeze(out)
        self.setData('out', out)
        self.setAttr('I/O Info:', val=(
            'file: {}\noutput dimensions: {}\ntype: {}\n'
            'Slice-sorted; RecViewer display intensity scaling applied.').format(
                filename, list(out.shape), out.dtype))
        return 0
