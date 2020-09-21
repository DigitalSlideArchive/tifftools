import os

import pytest

import tifftools

from .datastore import datastore


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
