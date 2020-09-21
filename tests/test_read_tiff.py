import io
import logging
import os

import pytest

import tifftools

from .datastore import datastore

LOGGER = logging.getLogger('tifftools')


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


def test_read_tiff_bad_stream():
    stream = io.BytesIO()
    stream.write(b'Not a tiff')
    with pytest.raises(Exception) as exc:
        tifftools.read_tiff(stream)
    assert 'Not a known tiff header' in str(exc.value)


@pytest.mark.parametrize('test_path,msg', [
    ('bad_tag_offset.tif', 'from desired offset'),
    ('bad_ifd_offset.tif', 'from desired offset'),
    ('bad_datatype.tif', 'Unknown datatype'),
    ('bad_double_reference.tif', 'double referenced'),
    ('bad_subifd_offset.tif', 'from desired offset'),
])
def test_read_tiff_warning_file(test_path, msg, caplog):
    path = os.path.join(os.path.dirname(__file__), 'data', test_path)
    with caplog.at_level(logging.WARNING):
        tifftools.read_tiff(path)
    assert msg in caplog.text
