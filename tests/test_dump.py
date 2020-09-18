import io
import json

import pytest

import tifftools

from .datastore import datastore


@pytest.mark.parametrize('test_path,num_ifds', [
    ('aperio_jp2k.svs', 6),
    ('hamamatsu.ndpi', 12),
    ('philips.ptif', 11),
    ('sample.subifd.ome.tif', 15),
    ('d043-200.tif', 4),
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
