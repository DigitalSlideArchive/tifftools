import logging
import os

import pytest

import tifftools

from .datastore import datastore


def test_split_one_subifd(tmp_path):
    path = datastore.fetch('sample.subifd.ome.tif')
    tifftools.tiff_split(str(path) + ',1,SubIFD:2', tmp_path / 'test')
    info = tifftools.read_tiff(tmp_path / 'testaaa.tif')
    assert len(info['ifds']) == 1
    assert int(tifftools.Tag.SubIFD) not in info['ifds'][0]['tags']


def test_split_subifds(tmp_path):
    path = datastore.fetch('sample.subifd.ome.tif')
    tifftools.tiff_split(str(path), tmp_path / 'test', subifds=True)
    info = tifftools.read_tiff(tmp_path / 'testaaa.tif')
    assert len(info['ifds']) == 1
    info = tifftools.read_tiff(tmp_path / 'testaao.tif')
    assert len(info['ifds']) == 1


def test_split_sub_subifds(tmp_path):
    path = datastore.fetch('subsubifds.tif')
    tifftools.tiff_split(str(path), tmp_path / 'test', subifds=True)
    info = tifftools.read_tiff(tmp_path / 'testaaa.tif')
    assert len(info['ifds']) == 1
    info = tifftools.read_tiff(tmp_path / 'testaai.tif')
    assert len(info['ifds']) == 1


@pytest.mark.parametrize('test_path,no_warnings', [
    ('aperio_jp2k.svs', True),
    ('hamamatsu.ndpi', False),
    ('philips.ptif', True),
    ('sample.subifd.ome.tif', True),
    ('d043-200.tif', True),
    ('subsubifds.tif', True),
])
def test_split_and_merge(test_path, no_warnings, tmp_path, caplog):
    path = datastore.fetch(test_path)
    destpath1 = tmp_path / ('initial' + os.path.splitext(test_path)[1])
    with caplog.at_level(logging.WARNING):
        tifftools.tiff_concat([path], destpath1)
        tifftools.tiff_split(path, tmp_path / 'test')
        components = sorted([tmp_path / p for p in os.listdir(tmp_path) if p.startswith('test')])
        destpath2 = tmp_path / ('merged' + os.path.splitext(test_path)[1])
        tifftools.tiff_merge(components, destpath2)
    assert not no_warnings or not caplog.text
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
    tifftools.tiff_merge([path], destpath1)
    tifftools.tiff_split(str(path) + ',0', tmp_path / 'test1')
    tifftools.tiff_split(str(path) + ',1', tmp_path / 'test2')
    tifftools.tiff_split(str(path) + ',2', tmp_path / 'test3')
    components = sorted([tmp_path / p for p in os.listdir(tmp_path) if p.startswith('test')])
    destpath2 = tmp_path / 'merged.tif'
    tifftools.tiff_concat(components, destpath2)
    chunksize = 1024 ** 2
    with open(destpath1, 'rb') as f1, open(destpath2, 'rb') as f2:
        while True:
            data1 = f1.read(chunksize)
            data2 = f2.read(chunksize)
            assert data1 == data2
            if not len(data1):
                break


@pytest.mark.parametrize('prefix,num,neededChars,result', [
    (None, 0, 3, './aaa.tif'),
    (None, 1, 4, './aaab.tif'),
    (None, 26, 3, './aba.tif'),
    ('prefix', 0, 3, 'prefixaaa.tif'),
])
def test_make_split_name(prefix, num, neededChars, result):
    assert tifftools.commands._make_split_name(prefix, num, neededChars) == result


def test_split_no_overwrite(tmp_path):
    path = datastore.fetch('subsubifds.tif')
    tifftools.tiff_split(str(path), tmp_path / 'test')
    with pytest.raises(Exception) as exc:
        tifftools.tiff_split(str(path), tmp_path / 'test')
    assert 'already exists' in str(exc.value)


def test_split_overwrite(tmp_path):
    path = datastore.fetch('subsubifds.tif')
    tifftools.tiff_split(str(path), tmp_path / 'test')
    mtime = os.path.getmtime(tmp_path / 'testaaa.tif')
    tifftools.tiff_split(str(path), tmp_path / 'test', overwrite=True)
    assert os.path.getmtime(tmp_path / 'testaaa.tif') != mtime
