import json

import pytest

import tifftools

from .datastore import datastore


@pytest.mark.parametrize('test_path,num_ifds', [
    ('aperio_jp2k.svs', 6),
    ('hamamatsu.ndpi', 12),
    ('philips.ptif', 11),
    ('sample.subifd.ome.tif', 15),
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
])
def test_tiff_dump_json(test_path, num_ifds, capsys):
    path = datastore.fetch(test_path)
    tifftools.tiff_dump(path, json=True)
    captured = capsys.readouterr()
    info = json.loads(captured.out)
    assert 'ifds' in info
