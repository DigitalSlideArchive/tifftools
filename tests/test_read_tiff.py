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
    ('subsubifds.tif', 3),
])
def test_read_tiff(test_path, num_ifds):
    path = datastore.fetch(test_path)
    info = tifftools.read_tiff(path)
    assert len(info['ifds']) == num_ifds


@pytest.mark.parametrize('test_path,msg', [
    ('notafile.tif', 'No such file'),
    ('bad_header1.tif', 'Not a known tiff header'),
    ('bad_header2.tif', 'Unexpected offset size'),
])
def test_read_tiff_bad_file(test_path, msg):
    path = os.path.join(os.path.dirname(__file__), 'data', test_path)
    with pytest.raises(Exception) as exc:
        tifftools.read_tiff(path)
    assert msg in str(exc.value)
