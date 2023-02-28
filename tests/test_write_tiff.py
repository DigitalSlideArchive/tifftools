import copy
import logging
import os

import pytest

import tifftools

from .datastore import datastore

LOGGER = logging.getLogger('tifftools')


def test_write_already_exists(tmp_path):
    path = datastore.fetch('d043-200.tif')
    info = tifftools.read_tiff(path)
    destpath = tmp_path / 'sample.tiff'
    tifftools.write_tiff(info, destpath)
    with pytest.raises(Exception) as exc:
        tifftools.write_tiff(info, destpath)
    assert 'File already exists' in str(exc.value)


def test_write_allow_existing(tmp_path):
    path = datastore.fetch('d043-200.tif')
    info = tifftools.read_tiff(path)
    destpath = tmp_path / 'sample.tiff'
    tifftools.write_tiff(info, destpath)
    len = os.path.getsize(destpath)
    tifftools.write_tiff(info, destpath, allowExisting=True)
    assert len == os.path.getsize(destpath)


def test_write_switch_to_bigtiff(tmp_path):
    path = datastore.fetch('hamamatsu.ndpi')
    info = tifftools.read_tiff(path)
    info['ifds'].extend(info['ifds'])
    info['ifds'].extend(info['ifds'])
    info['ifds'].extend(info['ifds'])
    destpath = tmp_path / 'sample.tiff'
    tifftools.write_tiff(info, destpath)
    destinfo = tifftools.read_tiff(destpath)
    assert destinfo['bigtiff'] is True


def test_write_bigtiff_from_datatype(tmp_path):
    path = os.path.join(os.path.dirname(__file__), 'data', 'good_single.tif')
    info = tifftools.read_tiff(path)
    info['ifds'][0]['tags'][23456] = {
        'datatype': tifftools.Datatype.LONG8,
        'data': [2**33],
    }
    destpath = tmp_path / 'sample.tiff'
    tifftools.write_tiff(info, destpath)
    destinfo = tifftools.read_tiff(destpath)
    assert destinfo['bigtiff'] is True


def test_write_downgrade_long8(tmp_path):
    path = os.path.join(os.path.dirname(__file__), 'data', 'good_single.tif')
    info = tifftools.read_tiff(path)
    info['ifds'][0]['tags'][23456] = {
        'datatype': tifftools.Datatype.LONG8,
        'data': [8],
    }
    destpath = tmp_path / 'sample.tiff'
    tifftools.write_tiff(info, destpath)
    destinfo = tifftools.read_tiff(destpath)
    assert destinfo['bigtiff'] is False


def test_write_downgrade_slong8(tmp_path):
    path = os.path.join(os.path.dirname(__file__), 'data', 'good_single.tif')
    info = tifftools.read_tiff(path)
    info['ifds'][0]['tags'][23456] = {
        'datatype': tifftools.Datatype.SLONG8,
        'data': [8],
    }
    destpath = tmp_path / 'sample.tiff'
    tifftools.write_tiff(info, destpath)
    destinfo = tifftools.read_tiff(destpath)
    assert destinfo['bigtiff'] is False


def test_write_bigtiff_with_long_data(tmp_path):
    path = datastore.fetch('hamamatsu.ndpi')
    info = tifftools.read_tiff(path)
    info['ifds'][0]['tags'][tifftools.Tag.FreeOffsets.value] = {
        'datatype': tifftools.Datatype.LONG,
        'data': [8],
    }
    info['ifds'][0]['tags'][tifftools.Tag.FreeByteCounts.value] = {
        'datatype': tifftools.Datatype.LONG,
        'data': [97044000],
    }
    info['ifds'].extend(info['ifds'])
    info['ifds'].extend(info['ifds'])
    destpath = tmp_path / 'sample.tiff'
    tifftools.write_tiff(info, destpath)
    destinfo = tifftools.read_tiff(destpath)
    assert destinfo['bigtiff'] is True


def test_write_bigtiff_with_offset_data(tmp_path):
    path = datastore.fetch('hamamatsu.ndpi')
    info = tifftools.read_tiff(path)
    info['ifds'][0]['tags'][tifftools.Tag.FreeOffsets.value] = {
        'datatype': tifftools.Datatype.LONG,
        'data': list(range(8, 8 + 256)),
    }
    info['ifds'][0]['tags'][tifftools.Tag.FreeByteCounts.value] = {
        'datatype': tifftools.Datatype.LONG,
        'data': [16777216] * 256,
    }
    destpath = tmp_path / 'sample.tiff'
    tifftools.write_tiff(info, destpath)
    destinfo = tifftools.read_tiff(destpath)
    assert destinfo['bigtiff'] is True


def test_write_bigtiff_with_repeated_offset_data(tmp_path):
    path = datastore.fetch('hamamatsu.ndpi')
    info = tifftools.read_tiff(path)
    info['ifds'][0]['tags'][tifftools.Tag.FreeOffsets.value] = {
        'datatype': tifftools.Datatype.LONG,
        'data': [8] * 256,
    }
    info['ifds'][0]['tags'][tifftools.Tag.FreeByteCounts.value] = {
        'datatype': tifftools.Datatype.LONG,
        'data': [16777216] * 256,
    }
    destpath = tmp_path / 'sample.tiff'
    tifftools.write_tiff(info, destpath)
    destinfo = tifftools.read_tiff(destpath)
    assert destinfo['bigtiff'] is False


def test_write_bytecount_data(tmp_path):
    path = os.path.join(os.path.dirname(__file__), 'data', 'good_single.tif')
    info = tifftools.read_tiff(path)
    # Just use data from within the file itself; an actual sample file with
    # compression 6 and defined Q, AC, and DC tables would be better.
    info['ifds'][0]['tags'][tifftools.Tag.JPEGQTables.value] = {
        'datatype': tifftools.Datatype.LONG,
        'data': [8],
    }
    destpath = tmp_path / 'sample.tiff'
    tifftools.write_tiff(info, destpath)
    assert os.path.getsize(destpath) > os.path.getsize(path) + 64


def test_write_single_subifd(tmp_path):
    path = os.path.join(os.path.dirname(__file__), 'data', 'good_single.tif')
    info = tifftools.read_tiff(path)
    info['ifds'][0]['tags'][tifftools.Tag.SubIFD.value] = {
        'ifds': [copy.deepcopy(info['ifds'][0])]
    }
    dest1path = tmp_path / 'sample1.tiff'
    tifftools.write_tiff(info, dest1path)
    dest1info = tifftools.read_tiff(dest1path)
    assert len(dest1info['ifds'][0]['tags'][tifftools.Tag.SubIFD.value]['ifds'][0]) == 1
    info = tifftools.read_tiff(path)
    info['ifds'][0]['tags'][tifftools.Tag.SubIFD.value] = {
        'ifds': [copy.deepcopy(info['ifds'])]
    }
    dest2path = tmp_path / 'sample2.tiff'
    tifftools.write_tiff(info, dest2path)
    dest2info = tifftools.read_tiff(dest2path)
    assert len(dest2info['ifds'][0]['tags'][tifftools.Tag.SubIFD.value]['ifds'][0]) == 1


def test_write_wrong_counts():
    path = os.path.join(os.path.dirname(__file__), 'data', 'good_single.tif')
    info = tifftools.read_tiff(path)
    info['ifds'][0]['tags'][tifftools.Tag.StripByteCounts.value]['data'].pop()
    with pytest.raises(Exception) as exc:
        tifftools.write_tiff(info, '-')
    assert 'Offsets and byte counts do not correspond' in str(exc.value)


def test_write_bad_strip_offset(tmp_path, caplog):
    path = os.path.join(os.path.dirname(__file__), 'data', 'bad_strip_offset.tif')
    info = tifftools.read_tiff(path)
    destpath = tmp_path / 'sample.tiff'
    with caplog.at_level(logging.WARNING):
        tifftools.write_tiff(info, destpath)
    assert 'from desired offset' in caplog.text
    destinfo = tifftools.read_tiff(destpath)
    assert destinfo['ifds'][0]['tags'][tifftools.Tag.StripOffsets.value]['data'][0] == 0


def test_write_new_ifd_without_fobj(tmp_path):
    path = datastore.fetch('d043-200.tif')
    info = tifftools.read_tiff(path)
    del info['ifds'][0]['tags'][tifftools.Tag.EXIFIFD.value]
    newifdentry = {'datatype': tifftools.Datatype.IFD, 'ifds': [[{'tags': {}}]]}
    info['ifds'][0]['tags'][tifftools.Tag.EXIFIFD.value] = newifdentry
    newifd = newifdentry['ifds'][0][0]
    newifd['tags'][tifftools.constants.EXIFTag.ExposureTime.value] = {
        'datatype': tifftools.Datatype.FLOAT, 'data': [10]}
    destpath = tmp_path / 'sample.tiff'
    tifftools.write_tiff(info, destpath)
    newinfo = tifftools.read_tiff(destpath)
    assert len(newinfo['ifds'][0]['tags'][tifftools.Tag.EXIFIFD.value]['ifds'][0][0]['tags']) == 1


def test_write_ifds_first(tmp_path):
    path = datastore.fetch('d043-200.tif')
    info = tifftools.read_tiff(path)
    destpath = tmp_path / 'sample.tiff'
    tifftools.write_tiff(info, destpath, ifdsFirst=True)
    len = os.path.getsize(destpath)
    tifftools.write_tiff(info, destpath, allowExisting=True)
    assert len == os.path.getsize(destpath)
