#!/usr/bin/env python
"""This module is a library of reader/writer routines for
DICOM data. To date this has only been tested on Philips DICOM data.
"""

import os
import pydicom
import pydicom.misc
import numpy as np
from collections import OrderedDict
from pydicom._uid_dict import UID_dictionary

# determine VR and endianess for data writing
def find_VR_endian_type(dataSet):
    transferSyntax = dataSet.file_meta.TransferSyntaxUID
    implicit_little = '1.2.840.10008.1.2'
    explicit_big = '1.2.840.10008.1.2.2'
    dataSet.is_implicit_VR = False
    dataSet.is_little_endian = True
    # if transferSyntax == pydicom.uid.ImplicitVRLitteEndian:
    if transferSyntax == implicit_little:
        dataSet.is_implicit_VR = True
    # elif transferSyntax == pydicom.uid.ExplicitVRBigEndian:
    elif transferSyntax == explicit_big:
        dataSet.is_little_endian = False
    return(dataSet)


# convert list of dictionaries back to sequence of datasets
def sqlist_to_sequence(slist):
    temp = []
    for item in slist:
        ds = pydicom.dataset.Dataset()
        for key in item.keys():
            tag = key_to_Tag(key)
            VR = item[key][1]
            val = item[key][2]
            if VR == 'SQ':
                val = sqlist_to_sequence(val)
            elif (VR == 'UI'):
                val = uidname_to_val(val)
            else:
                val = eval(val)
            ds.add_new(tag, VR, val)
        temp.append(ds)
    return pydicom.Sequence(temp)


# find UI name from pydicom UID_dictionary and return its original value
def uidname_to_val(name):
    is_entry = False
    for key, val in UID_dictionary.items():
        if val[0] == name:
            is_entry = True
            break
    if is_entry:
        return(key)
    else:
        return(name)


# create a Pydicom Dataset for one image from the GPI DICOM dictionary
# and data for that image
def dict_to_data_set(data, dicomdict):
    ds = pydicom.dataset.Dataset()
    ds.ensure_file_meta()
    for key in dicomdict.keys():
        tag = key_to_Tag(key)
        VR = dicomdict[key][1]
        val = dicomdict[key][2]
        if VR == 'SQ':
            val = sqlist_to_sequence(val)
        elif (VR == 'UI'):
            val = uidname_to_val(val)
        else:
            val = eval(val)
        if ('0002,' in key or '0000,' in key):
            ds.file_meta.add_new(tag, VR, val)
        else:
            ds.add_new(tag, VR, val)
    ds.PixelData = data.tobytes()
    ds = find_VR_endian_type(ds)
    return ds


# Convert a Pydicom Dataset element to a dictionary key/value pair
def data_elem_to_dict(dsItem):
    # str(DataElement) formats/truncates large values (e.g. big sequences),
    # so it's not cheap -- call it once instead of once per field.
    text = str(dsItem)
    key = text[0:12]
    desc = text[13:48]
    VR = text[49:51]
    val = text[53::]
    value = [desc, VR, val]
    return key, value


# Convert GPI DICOM dictionary key string into a Pydicom Dataset Tag
def key_to_Tag(dictKey):
    group = '0x'+dictKey[1:5]
    elem = '0x'+dictKey[7:11]
    return pydicom.tag.Tag(group, elem)


# recurse through sequence objects to generate list of dictionary
def seq_to_sqlist(seq, anonymize):
    sqlist = []
    for item in seq.value:
        temp = OrderedDict()
        for line in item:
            key, value = data_elem_to_dict(line)
            if line.VR == 'SQ':
                value[2] = seq_to_sqlist(line, anonymize)
            if anonymize and (value[1] == 'PN' or '0010,' in key):
                value[2] = "''"
            temp[key] = value
        sqlist.append(dict(temp))
    return sqlist


def _read_dicomdir(DicomDir):
    try:
        from pydicom.filereader import read_dicomdir
    except ImportError:
        from pydicom.fileset import FileSet
        return FileSet(DicomDir)._tree
    return read_dicomdir(DicomDir)


def _record(dataset_or_node):
    return getattr(dataset_or_node, '_record', dataset_or_node)


def _dicomdir_patients(dicom_dir):
    return (dicom_dir.patient_records if hasattr(dicom_dir, 'patient_records')
            else dicom_dir.children)


def _image_paths(series, basedir):
    paths = []
    for image in series.children:
        image_record = _record(image)
        if getattr(image_record, 'DirectoryRecordType', '') != 'IMAGE':
            continue
        file_id = getattr(image_record, 'ReferencedFileID', None)
        if not file_id:
            continue
        if isinstance(file_id, str):
            file_id = file_id.replace('\\', '/').split('/')
        path = os.path.join(basedir, *[str(part) for part in file_id])
        if os.path.isfile(path):
            paths.append(path)
    return paths


# Read the Pydicom Dataset and fill a GPI DICOM dictionary
def fill_dicom_dict(dataSet, anonymize):
    imgDict = OrderedDict()
    for line in dataSet.file_meta:
        key, value = data_elem_to_dict(line)
        imgDict[key] = value
    for line in dataSet:
        key, value = data_elem_to_dict(line)
        if line.VR == 'SQ':
            value[2] = seq_to_sqlist(line, anonymize)
        if key == '(7fe0, 0010)':  # don't need to worry about pixel element
            continue
        if anonymize and (value[1] == 'PN' or '0010,' in key):
            value[2] = "''"
        imgDict[key] = value
    return imgDict


def get_series_info(DicomDir):
    # adapted from plot_read_dicom_directory at
    # https://pydicom.github.io/pydicom/stable/auto_examples/input_output/plot_read_dicom_directory.html
    info = {}
    series_num = []
    protocols = []
    series_uids = []
    labels = []
    # find all Series in the folder
    dicom_dir = _read_dicomdir(DicomDir)
    patient_records = _dicomdir_patients(dicom_dir)
    for patient_record in patient_records:
        patient = getattr(patient_record, '_record', patient_record)
        if hasattr(patient, 'PatientID') or hasattr(patient, 'PatientName'):
            studies = patient_record.children
            for study in studies:
                study_record = getattr(study, '_record', study)
                all_series = study.children
                for series in all_series:
                    series_record = getattr(series, '_record', series)
                    image_paths = _image_paths(series, os.path.dirname(DicomDir))
                    if (getattr(series_record, 'DirectoryRecordType', '') == 'SERIES' and
                            hasattr(series_record, 'SeriesNumber') and image_paths):
                        series_uid = str(getattr(series_record, 'SeriesInstanceUID', ''))
                        series_number = str(series_record.SeriesNumber)
                        protocol = str(getattr(series_record, 'ProtocolName', ''))
                        patient_name = str(getattr(patient, 'PatientName', ''))
                        study_date = str(getattr(study_record, 'StudyDate', ''))
                        series_num.append(series_number)
                        protocols.append(protocol)
                        series_uids.append(series_uid)
                        labels.append('{} | {} | {} | {} | {} [{}]'.format(
                            patient_name, study_date, series_number, protocol,
                            getattr(series_record, 'Modality', ''), series_uid))
    info['series'] = series_num
    info['protocol'] = protocols
    info['series_uids'] = series_uids
    info['labels'] = labels
    return info


def gen_dicom_list(DicomDir, refSeries):
    basedir = os.path.dirname(DicomDir)
    lstFilesDCM = []  # create an empty list
    dicom_dir = _read_dicomdir(DicomDir)
    patient_records = _dicomdir_patients(dicom_dir)
    selected_uid = ''
    selected_number = str(refSeries)
    if '[' in str(refSeries) and ']' in str(refSeries):
        selected_uid = str(refSeries).rsplit('[', 1)[1].split(']', 1)[0]
    if ' | ' in str(refSeries):
        selected_number = str(refSeries).split(' | ')[2]
    for patient_record in patient_records:
        patient = getattr(patient_record, '_record', patient_record)
        if hasattr(patient, 'PatientID') or hasattr(patient, 'PatientName'):
            studies = patient_record.children
            for study in studies:
                all_series = study.children
                for series in all_series:
                    series_record = getattr(series, '_record', series)
                    matches_uid = selected_uid and str(
                        getattr(series_record, 'SeriesInstanceUID', '')) == selected_uid
                    matches_number = str(getattr(series_record, 'SeriesNumber', '')) == selected_number
                    if matches_uid or (not selected_uid and matches_number):
                        lstFilesDCM.extend(_image_paths(series, basedir))

    return lstFilesDCM


# find all files in a directory that are DICOM images
# adapted from python_dicom_load_pydicom.py at
# https://gist.github.com/somada141/8dd67a02e330a657cf9e
def dicom_file_list(baseDir):
    lstFilesDCM = []

    for dirName, _, fileList in os.walk(baseDir):
        for filename in sorted(fileList):
            filename = os.path.join(dirName, filename)
            if os.path.basename(filename).upper() == 'DICOMDIR':
                continue
            # Cheap preamble/magic check instead of a full dcmread(): the
            # header (incl. any large private sequences) gets parsed for
            # real in load_dicom() below, so doing it again here just to
            # test validity doubles the metadata-parsing cost for large series.
            try:
                if not pydicom.misc.is_dicom(filename):
                    continue
            except OSError:
                continue
            lstFilesDCM.append(filename)

    return lstFilesDCM


# Load images from a DICOM folder
# adapted from python_dicom_load_pydicom.py at
# https://gist.github.com/somada141/8dd67a02e330a657cf9e
#
# Frames are organized into an (N-dimensional) grid instead of one flat
# slice axis: one axis per non-spatial DICOM attribute that actually varies
# across the series (dynamic/temporal position, echo, mag/phase/real/imag,
# cardiac trigger delay, b-value, stack ID), plus a physically-derived slice
# axis. This is a best-effort grid, not a strict requirement -- missing
# combinations are left zero-filled and colliding ones keep the first frame,
# both reported back in the metadata rather than silently flattening
# everything onto one axis or raising.

# labels for the non-spatial axes _stack_key() distinguishes, in tuple order
_STACK_DIM_LABELS = ('dynamic', 'echo', 'image_type', 'trigger_time', 'b_value', 'stack_id')

_ROUND_NDIGITS = 3  # mm; collapses float jitter in computed slice coordinates


def _image_type_component(ds):
    """Best-effort MAG/PHASE/REAL/IMAG classification from (0008,0008).

    Returns 'OTHER' (a single, constant value across a normal series) rather
    than guessing 'M' when the tag doesn't say -- guessing would silently
    merge genuinely different image types into one bucket.
    """
    for value in getattr(ds, 'ImageType', []):
        code = str(value).upper()
        if code in ('M', 'MAGNITUDE'):
            return 'M'
        if code in ('P', 'PHASE'):
            return 'P'
        if code in ('R', 'REAL'):
            return 'R'
        if code in ('I', 'IMAGINARY'):
            return 'I'
    return 'OTHER'


def _tag_value(ds, name):
    val = getattr(ds, name, None)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return str(val)


def _stack_key(ds):
    """Non-spatial coordinate identifying which 3D volume a frame belongs to,
    so dynamics/echoes/mag-phase-real-imag/cardiac-phases/b-values aren't
    flattened onto the slice axis. Falls back to AcquisitionNumber for
    scanners that don't populate TemporalPositionIdentifier on dynamic scans.
    """
    dynamic = _tag_value(ds, 'TemporalPositionIdentifier')
    if dynamic is None:
        dynamic = _tag_value(ds, 'AcquisitionNumber')
    return (dynamic, _tag_value(ds, 'EchoNumbers'), _image_type_component(ds),
             _tag_value(ds, 'TriggerTime'), _tag_value(ds, 'DiffusionBValue'),
             _tag_value(ds, 'StackID'))


def _slice_coordinate(ds):
    """Physical position of a frame along the slice-normal direction, so
    identical anatomical slices line up across dynamics/echoes even on
    oblique acquisitions. Falls back to SliceLocation, then None (caller
    falls back to acquisition order) when geometry tags are missing.
    """
    iop = getattr(ds, 'ImageOrientationPatient', None)
    ipp = getattr(ds, 'ImagePositionPatient', None)
    if iop is not None and ipp is not None and len(iop) == 6 and len(ipp) == 3:
        try:
            row = np.array([float(v) for v in iop[0:3]])
            col = np.array([float(v) for v in iop[3:6]])
            normal = np.cross(row, col)
            pos = np.array([float(v) for v in ipp])
            return round(float(np.dot(normal, pos)), _ROUND_NDIGITS)
        except (TypeError, ValueError):
            pass
    if ipp is not None and len(ipp) >= 3:
        try:
            return round(float(ipp[2]), _ROUND_NDIGITS)
        except (TypeError, ValueError):
            pass
    sl = getattr(ds, 'SliceLocation', None)
    if sl is not None:
        try:
            return round(float(sl), _ROUND_NDIGITS)
        except (TypeError, ValueError):
            pass
    return None


def _acquisition_order_key(frame):
    ds = frame['ds']
    return (int(getattr(ds, 'InstanceNumber', 0)),
            str(getattr(ds, 'SOPInstanceUID', frame['filename'])), frame['frame_index'])


def _sort_unique(values):
    return sorted(values, key=lambda v: (v is None, v))


def load_dicom(lstFilesDCM, anonymize, apply_lut=False, return_metadata=False):
    if not lstFilesDCM:
        raise ValueError('No DICOM image files were found.')
    dicomdict = OrderedDict()
    datasets = []
    image_shape = None

    for filenameDCM in lstFilesDCM:
        try:
            ds = pydicom.dcmread(filenameDCM)
            datasets.append((filenameDCM, ds))
        except (OSError, pydicom.errors.InvalidDicomError, AttributeError,
                ValueError) as exc:
            raise ValueError('Failed to read DICOM header {}: {}'.format(filenameDCM, exc)) from exc

    frames = []
    for filenameDCM, ds in datasets:
        try:
            pixels = np.asarray(ds.pixel_array)
            if apply_lut:
                from pydicom.pixels import apply_modality_lut
                pixels = np.asarray(apply_modality_lut(pixels, ds))
        except (NotImplementedError, RuntimeError) as exc:
            message = ('Pixel data for {} could not be decoded. Install a '
                       'pydicom-compatible decoder such as pylibjpeg or GDCM: {}')
            raise ValueError(message.format(filenameDCM, exc)) from exc
        except (AttributeError, ValueError) as exc:
            raise ValueError('Failed to read DICOM image {}: {}'.format(filenameDCM, exc)) from exc

        if pixels.ndim == 2:
            pixels = pixels[np.newaxis, ...]
        elif pixels.ndim != 3:
            raise ValueError('Unsupported pixel dimensions in {}: {}'.format(filenameDCM, pixels.shape))

        if image_shape is None:
            image_shape = pixels.shape[1:]
        if pixels.shape[1:] != image_shape:
            raise ValueError('DICOM images have inconsistent dimensions: {} has {}, expected {}'.format(
                filenameDCM, pixels.shape[1:], image_shape))

        for frame_index in range(len(pixels)):
            frames.append({
                'pixels': pixels[frame_index],
                'ds': ds,
                'filename': filenameDCM,
                'frame_index': frame_index,
            })
        dicomdict[os.path.basename(filenameDCM)] = fill_dicom_dict(ds, anonymize)

    # non-spatial grouping: which 3D volume (dynamic/echo/mag-phase/etc) each
    # frame belongs to.
    stack_keys = [_stack_key(f['ds']) for f in frames]
    candidate_dims = [i for i in range(len(_STACK_DIM_LABELS))
                       if len({key[i] for key in stack_keys}) > 1]
    # keep a candidate axis only if it isn't fully determined by the axes
    # already kept (e.g. TriggerTime is often just a per-dynamic timestamp
    # that mirrors TemporalPositionIdentifier one-to-one; treating both as
    # separate grid axes would blow up the grid with mostly-empty slots).
    varying_dims = []
    redundant_dims = []
    for i in candidate_dims:
        seen = {}
        redundant = True
        for key in stack_keys:
            reduced = tuple(key[d] for d in varying_dims)
            vals = seen.setdefault(reduced, set())
            vals.add(key[i])
            if len(vals) > 1:
                redundant = False
                break
        if redundant:
            redundant_dims.append(_STACK_DIM_LABELS[i])
        else:
            varying_dims.append(i)
    value_lists = [_sort_unique({key[i] for key in stack_keys}) for i in varying_dims]
    value_index = [{v: idx for idx, v in enumerate(values)} for values in value_lists]
    grid_shape = [len(values) for values in value_lists]

    # slice axis: physical position when every frame has one, else fall back
    # to per-volume acquisition order (assumes slice varies fastest/slowest
    # consistently across volumes, same as classic flat DICOM stacking).
    positions = [_slice_coordinate(f['ds']) for f in frames]
    use_position = all(p is not None for p in positions)
    if use_position:
        for frame, pos in zip(frames, positions):
            frame['slice_key'] = pos
        slice_values = _sort_unique({f['slice_key'] for f in frames})
    else:
        groups = OrderedDict()
        for frame, key in zip(frames, stack_keys):
            groups.setdefault(key, []).append(frame)
        for group in groups.values():
            group.sort(key=_acquisition_order_key)
            for rank, f in enumerate(group):
                f['slice_key'] = rank
        slice_values = list(range(max(len(g) for g in groups.values())))
    slice_index = {v: idx for idx, v in enumerate(slice_values)}
    nslices = len(slice_values)

    out_shape = tuple(grid_shape) + (nslices,) + image_shape
    out = np.zeros(out_shape, dtype=frames[0]['pixels'].dtype)
    filled = np.zeros(tuple(grid_shape) + (nslices,), dtype=bool)
    frame_metadata_grid = {}
    collisions = 0

    for frame, key in zip(frames, stack_keys):
        grid_idx = tuple(value_index[d][key[varying_dims[d]]] for d in range(len(varying_dims)))
        full_idx = grid_idx + (slice_index[frame['slice_key']],)
        if filled[full_idx]:
            collisions += 1
            continue
        filled[full_idx] = True
        out[full_idx] = frame['pixels']
        ds = frame['ds']
        frame_metadata_grid[full_idx] = {
            'source': os.path.basename(frame['filename']),
            'frame': frame['frame_index'],
            'image_position': list(getattr(ds, 'ImagePositionPatient', [])),
            'instance_number': getattr(ds, 'InstanceNumber', None),
        }

    missing = int(filled.size - int(filled.sum()))
    frame_metadata = [frame_metadata_grid.get(idx) for idx in np.ndindex(*out_shape[:-len(image_shape)])]

    dim_labels = [_STACK_DIM_LABELS[i] for i in varying_dims] + ['slice']
    dim_values = value_lists + [slice_values]

    if not return_metadata:
        return out, dict(dicomdict)

    first_ds = datasets[0][1]
    metadata = {
        'spacing': list(getattr(first_ds, 'PixelSpacing', [])) + [
            getattr(first_ds, 'SpacingBetweenSlices',
                    getattr(first_ds, 'SliceThickness', None))],
        'origin': list(getattr(first_ds, 'ImagePositionPatient', [])),
        'orientation': list(getattr(first_ds, 'ImageOrientationPatient', [])),
        'series_instance_uid': str(getattr(first_ds, 'SeriesInstanceUID', '')),
        'study_instance_uid': str(getattr(first_ds, 'StudyInstanceUID', '')),
        'dim_labels': dim_labels,
        'dim_values': dim_values,
        'redundant_dims': redundant_dims,
        'missing_frames': missing,
        'colliding_frames': collisions,
        'frames': frame_metadata,
    }
    return out, dict(dicomdict), metadata
