import os

import pytest

import tifftools

from .datastore import datastore


@pytest.mark.parametrize('test_path,num_ifds', [
    ('aperio_jp2k.svs', 6),
    ('hamamatsu.ndpi', 12),
    ('philips.ptif', 11),
    ('sample.subifd.ome.tif', 3),
    ('d043-200.tif', 2),
])
def test_read_tiff(test_path, num_ifds):
    path = datastore.fetch(test_path)
    info = tifftools.read_tiff(path)
    assert len(info['ifds']) == num_ifds


@pytest.mark.parametrize('test_path', [
    'aperio_jp2k.svs',
    'hamamatsu.ndpi',
    'philips.ptif',
    'sample.subifd.ome.tif',
    'd043-200.tif',
])
def test_split_and_merge(test_path, tmp_path):
    path = datastore.fetch(test_path)
    destpath1 = tmp_path / ('initial' + os.path.splitext(test_path)[1])
    tifftools.tiff_concat(destpath1, [path])
    tifftools.tiff_split(path, tmp_path / 'test')
    components = sorted([tmp_path / p for p in os.listdir(tmp_path) if p.startswith('test')])
    destpath2 = tmp_path / ('merged' + os.path.splitext(test_path)[1])
    tifftools.tiff_merge(destpath2, components)
    chunksize = 1024 ** 2
    with open(destpath1, 'rb') as f1, open(destpath2, 'rb') as f2:
        while True:
            data1 = f1.read(chunksize)
            data2 = f2.read(chunksize)
            assert data1 == data2
            if not len(data1):
                break


def test_split_and_merge_by_ifd(tmp_path):
    path = datastore.fetch('sample.subifd.ome.tif')
    destpath1 = tmp_path / 'initial.tif'
    tifftools.tiff_merge(destpath1, [path])
    tifftools.tiff_split(str(path) + ',0', tmp_path / 'test1')
    tifftools.tiff_split(str(path) + ',1', tmp_path / 'test2')
    tifftools.tiff_split(str(path) + ',2', tmp_path / 'test3')
    components = sorted([tmp_path / p for p in os.listdir(tmp_path) if p.startswith('test')])
    destpath2 = tmp_path / 'merged.tif'
    tifftools.tiff_concat(destpath2, components)
    chunksize = 1024 ** 2
    with open(destpath1, 'rb') as f1, open(destpath2, 'rb') as f2:
        while True:
            data1 = f1.read(chunksize)
            data2 = f2.read(chunksize)
            assert data1 == data2
            if not len(data1):
                break
