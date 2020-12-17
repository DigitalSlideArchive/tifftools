import io
import json
import os

import pytest

import tifftools

from .datastore import datastore


@pytest.mark.parametrize('test_path,num_ifds', [
    ('aperio_jp2k.svs', 6),
    ('hamamatsu.ndpi', 12),
    ('philips.ptif', 11),
    ('sample.subifd.ome.tif', 15),
    ('d043-200.tif', 4),
    ('subsubifds.tif', 9),
])
def test_tiff_dump(test_path, num_ifds, capsys):
    path = datastore.fetch(test_path)
    tifftools.tiff_dump(path)
    captured = capsys.readouterr()
    assert len(captured.out.split('Directory ')) == num_ifds + 1


@pytest.mark.parametrize('test_path,num_ifds', [
    ('aperio_jp2k.svs', 6),
    ('hamamatsu.ndpi', 12),
    ('philips.ptif', 11),
    ('sample.subifd.ome.tif', 15),
    ('d043-200.tif', 4),
    ('subsubifds.tif', 9),
])
def test_tiff_dump_json(test_path, num_ifds, capsys):
    path = datastore.fetch(test_path)
    tifftools.tiff_dump(path, json=True)
    captured = capsys.readouterr()
    info = json.loads(captured.out)
    assert 'ifds' in info


@pytest.mark.parametrize('test_path,num_ifds', [
    ('aperio_jp2k.svs', 6),
    ('hamamatsu.ndpi', 12),
    ('philips.ptif', 11),
    ('sample.subifd.ome.tif', 15),
    ('d043-200.tif', 4),
    ('subsubifds.tif', 9),
])
def test_tiff_dump_to_stream(test_path, num_ifds):
    path = datastore.fetch(test_path)
    dest = io.StringIO()
    tifftools.tiff_dump(path, dest=dest)
    assert len(dest.getvalue().split('Directory ')) == num_ifds + 1
    # Ensure dump and info produce the same results
    destinfo = io.StringIO()
    tifftools.tiff_info(path, dest=destinfo)
    assert dest.getvalue() == destinfo.getvalue()


@pytest.mark.parametrize('suffix,num_ifds', [
    ('', 9),
    (',0', 1),
    (',1', 7),
    (',1,0', 1),
    (',1,1', 4),
    (',1,SubIFD:1', 4),
    (',1,330:1', 4),
    (',1,0x14a:1', 4),
    (',1,SubIFD:1,0', 1),
    (',1,SubIFD:1,1', 3),
    (',1,SubIFD:1,1,SubIFD:0', 2),
    (',1,SubIFD:1,1,SubIFD:0,1', 1),
])
def test_tiff_dump_specific_ifd(suffix, num_ifds, capsys):
    path = datastore.fetch('subsubifds.tif')
    tifftools.tiff_dump(path + suffix)
    captured = capsys.readouterr()
    assert len(captured.out.split('Directory ')) == num_ifds + 1


def test_tiff_dump_multiple(capsys):
    path1 = datastore.fetch('d043-200.tif')
    path2 = datastore.fetch('subsubifds.tif')
    tifftools.tiff_dump([path1, path2])
    captured = capsys.readouterr()
    assert len(captured.out.split('Directory ')) == 4 + 9 + 1


def test_tiff_dump_multiple_json(capsys):
    path1 = datastore.fetch('d043-200.tif')
    path2 = datastore.fetch('subsubifds.tif')
    tifftools.tiff_dump([path1, path2], json=True)
    captured = capsys.readouterr()
    info = json.loads(captured.out)
    assert path1 in info
    assert path2 in info
    assert 'ifds' in info[path1]


def test_tiff_dump_jpeq_quality(capsys):
    path = os.path.join(os.path.dirname(__file__), 'data', 'good_jpeg.tif')
    tifftools.tiff_dump(path)
    captured = capsys.readouterr()
    assert 'estimated quality' in captured.out


@pytest.mark.parametrize('test_path', [
    'bad_jpeg.tif',
    'bad_jpeg2.tif',
])
def test_tiff_dump_jpeq_quality_bad(test_path, capsys):
    path = os.path.join(os.path.dirname(__file__), 'data', test_path)
    tifftools.tiff_dump(path)
    captured = capsys.readouterr()
    assert 'estimated quality' not in captured.out
