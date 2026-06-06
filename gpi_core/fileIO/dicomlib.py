#!/usr/bin/env python
"""This module is a library of reader/writer routines for
DICOM data. To date this has only been tested on Philips DICOM data.
"""

import os
import pydicom
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
    key = str(dsItem)[0:12]
    desc = str(dsItem)[13:48]
    VR = str(dsItem)[49:51]
    val = str(dsItem)[53::]
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
    from pydicom.filereader import read_dicomdir
    info = {}
    series_num = []
    protocols = [] #create an empty list
    # find all Series in the folder
    dicom_dir = read_dicomdir(DicomDir)
    for patient_record in dicom_dir.patient_records:
        if (hasattr(patient_record, 'PatientID') and
                hasattr(patient_record, 'PatientName')):
            studies = patient_record.children
            for study in studies:
                all_series = study.children
                for series in all_series:
                    if (hasattr(series, 'SeriesNumber') and
                        hasattr(series, 'ProtocolName')):
                        if int(series.SeriesNumber) > 0:
                            series_num.append(series.SeriesNumber)
                            protocols.append(series.ProtocolName)
    info['series'] = series_num
    info['protocol'] = protocols
    return info


def gen_dicom_list(DicomDir, refSeries):
    from pydicom.filereader import read_dicomdir
    basedir = os.path.dirname(DicomDir)+'/DICOM'
    lstFilesDCM = []  # create an empty list
    dicom_dir = read_dicomdir(DicomDir)
    for patient_record in dicom_dir.patient_records:
        if (hasattr(patient_record, 'PatientID') and
                hasattr(patient_record, 'PatientName')):
            studies = patient_record.children
            for study in studies:
                all_series = study.children
                for series in all_series:
                    if (int(series.SeriesNumber) == int(refSeries)):
                        data = series.children
                        for img in data:
                            fileID = img.ReferencedFileID
                            imgtype = img.DirectoryRecordType
                            if(fileID[0] == 'DICOM' and imgtype == 'IMAGE'):
                                if(len(fileID) == 3):
                                    filename = basedir+'/'+fileID[1]+'/'+fileID[2]
                                else:
                                    filename = basedir+'/'+fileID[1]
                                lstFilesDCM.append(filename)

    return lstFilesDCM


# find all files in a directory that are DICOM images
# adapted from python_dicom_load_pydicom.py at
# https://gist.github.com/somada141/8dd67a02e330a657cf9e
def dicom_file_list(baseDir):
    lstFilesDCM = []

    for dirName, subdirList, fileList in os.walk(baseDir):
        for filename in sorted(fileList):
            if ".dcm" in filename.lower() or "im" in filename.lower():  # check whether the file's DICOM
                lstFilesDCM.append(os.path.join(dirName,filename))

    return lstFilesDCM


# Load images from a DICOM folder
# adapted from python_dicom_load_pydicom.py at
# https://gist.github.com/somada141/8dd67a02e330a657cf9e
def load_dicom(lstFilesDCM, anonymize):

    dicomdict = OrderedDict()
    # Get ref file
    RefDs = pydicom.dcmread(lstFilesDCM[0])

    # Load dimensions based on the number of rows, columns, and slices (along the Z axis)
    ConstPixelDims = (len(lstFilesDCM), int(RefDs.Columns), int(RefDs.Rows))

    # The array is sized based on 'ConstPixelDims'
    ArrayDicom = np.zeros(ConstPixelDims, dtype=RefDs.pixel_array.dtype)

    # loop through all the DICOM files
    for filenameDCM in lstFilesDCM:
        # read the file
        try:
            ds = pydicom.dcmread(filenameDCM)
        except:
            print('failed to read '+str(filenameDCM)+' data.')

        # copy DICOM header info to dictionary

        # store the raw image data
        try:
            base = os.path.basename(filenameDCM)
            # fill in the dictionary for the image
            dicomdict[base] = fill_dicom_dict(ds, anonymize)
            # grab the data
            ArrayDicom[lstFilesDCM.index(filenameDCM), :, :] = ds.pixel_array
        except:
            pass

    return ArrayDicom, dict(dicomdict)
