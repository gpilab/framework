from pathlib import Path
import xml.etree.ElementTree as ET

import gpi
import numpy as np


def read_rec(filename):
    """Read a PRIDE_V5 XML/REC pair as (image, row, column) display values.

    Images are grouped by acquisition keys, then sorted by slice number.
    REC offsets come from each image's zero-based Index, not XML order.
    No anatomical reorientation or Philips floating-point scaling is applied.
    """
    path = Path(filename)
    if path.suffix.lower() not in ('.xml', '.rec'):
        raise ValueError('Select a PRIDE .xml or .rec file.')
    xml_path = path.with_suffix('.xml')
    rec_path = path.with_suffix('.rec')
    if path.suffix.lower() == '.xml':
        xml_path = path
    else:
        rec_path = path
    if not xml_path.is_file() or not rec_path.is_file():
        raise ValueError('Both XML and REC files with the same base name are required.')

    root = ET.parse(xml_path).getroot()
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
        if width <= 0 or height <= 0 or index < 0:
            raise ValueError('Image dimensions must be positive and Index nonnegative.')
        if bits not in (8, 16) or representation not in (0, 1):
            raise ValueError('Only signed/unsigned 8-bit and 16-bit REC pixels are supported.')
        if not np.isfinite(slope) or not np.isfinite(intercept):
            raise ValueError('Rescale Slope and Rescale Intercept must be finite.')
        dtype = np.dtype('<{}{}'.format('i' if representation else 'u', bits // 8))
        records.append((order, index, height, width, dtype, slope, intercept))

    _, _, height, width, dtype, _, _ = records[0]
    if any(record[2:5] != (height, width, dtype) for record in records):
        raise ValueError('All images must have the same dimensions and pixel storage type.')
    indices = [record[1] for record in records]
    if sorted(indices) != list(range(len(records))):
        raise ValueError('REC image indices must be unique and contiguous starting at zero.')
    frame_bytes = height * width * dtype.itemsize
    expected_bytes = len(records) * frame_bytes
    if rec_path.stat().st_size != expected_bytes:
        raise ValueError('REC size does not match XML: expected {} bytes, found {}.'.format(
            expected_bytes, rec_path.stat().st_size))

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
    return out


class ExternalNode(gpi.NodeAPI):
    """Read a PRIDE_V5 XML/REC pair for connection to ImageDisplay.

    Select either file; its same-name companion must be in the same folder.
    out: float32 (image, row, column), grouped by acquisition and slice-sorted.
    Values use RecViewer display scaling: stored * Rescale Slope + Intercept.
    """

    def execType(self):
        return gpi.GPI_PROCESS

    def initUI(self):
        self.addWidget('TextBox', 'I/O Info:')
        self.addWidget('OpenFileBrowser', 'File Browser',
                       button_title='Browse', caption='Open XML/REC File',
                       filter='PRIDE XML/REC (*.xml *.rec *.XML *.REC);;All files (*)')
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
        self.setData('out', out)
        self.setAttr('I/O Info:', val=(
            'file: {}\ndimensions (image, row, column): {}\ntype: {}\n'
            'Slice-sorted; RecViewer display intensity scaling applied.').format(
                filename, list(out.shape), out.dtype))
        return 0
