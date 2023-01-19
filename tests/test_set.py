import io
import logging
import shutil

import pytest

import tifftools

from .datastore import datastore

LOGGER = logging.getLogger('tifftools')


@pytest.mark.parametrize('setlist,ifdspec,tag,datavalue', [
    ([('ImageDescription', 'Dog digging')], '', tifftools.Tag.ImageDescription, 'Dog digging'),
    ([('Orientation', '2')], '', tifftools.Tag.Orientation, [2]),
    ([('FNumber,0,EXIFIFD:0', '54,10')], ',0,EXIFIFD:0',
     tifftools.constants.EXIFTag.FNumber, [54, 10]),
    ([('FNumber,0,EXIFIFD:0', '0x36,0x0000A')], ',0,EXIFIFD:0',
     tifftools.constants.EXIFTag.FNumber, [54, 10]),
    ([('FNumber:DOUBLE,0,EXIFIFD:0', '5.4')], ',0,EXIFIFD:0',
     tifftools.constants.EXIFTag.FNumber, [5.4]),
    ([('FNumber,0,EXIFIFD:0', '0x36,0x0A')], ',0,EXIFIFD:0',
     tifftools.constants.EXIFTag.FNumber, [54, 10]),
    ([('BadFaxLines', '65537')], '', tifftools.Tag.BadFaxLines, [65537]),
    ([('BadFaxLines', '1.2')], '', tifftools.Tag.BadFaxLines, [1.2]),
    ([('23456', '123')], '', 23456, [123]),
    ([('23456', '123 -4567')], '', 23456, [123, -4567]),
    ([('23456', b'Value')], '', 23456, 'Value'),
    ([('23456', b'\xFFValue')], '', 23456, b'\xFFValue'),
])
def test_tiff_set(tmp_path, setlist, ifdspec, tag, datavalue):
    path = datastore.fetch('d043-200.tif')
    dest = tmp_path / 'results.tif'
    tifftools.tiff_set(path, dest, setlist=setlist)
    info = tifftools.read_tiff(str(dest) + ifdspec)
    assert info['ifds'][0]['tags'][int(tag)]['data'] == datavalue


@pytest.mark.parametrize('unsetlist,ifdspec,tag', [
    (['ImageDescription'], '', tifftools.Tag.ImageDescription),
    (['Orientation'], '', tifftools.Tag.Orientation),
    (['FNumber,0,EXIFIFD:0'], ',0,EXIFIFD:0',
     tifftools.constants.EXIFTag.FNumber),
])
def test_tiff_set_unset(tmp_path, unsetlist, ifdspec, tag):
    path = datastore.fetch('d043-200.tif')
    dest = tmp_path / 'results.tif'
    tifftools.tiff_set(path, dest, unset=unsetlist)
    info = tifftools.read_tiff(str(dest) + ifdspec)
    assert int(tag) not in info['ifds'][0]['tags']


def test_tiff_set_setfrom(tmp_path):
    path = datastore.fetch('d043-200.tif')
    dest = tmp_path / 'results.tif'
    tifftools.tiff_set(str(path) + ',1', dest, setfrom=[('Model', path)])
    info = tifftools.read_tiff(str(dest))
    assert info['ifds'][0]['tags'][int(tifftools.Tag.Model)]['data'] == 'NIKON D500'


def test_tiff_set_self(tmp_path):
    path = datastore.fetch('d043-200.tif')
    dest = tmp_path / 'results.tif'
    shutil.copy(path, dest)
    with pytest.raises(tifftools.exceptions.TifftoolsError):
        tifftools.tiff_set(dest, setlist=[('ImageDescription', 'Dog digging')])
    info = tifftools.read_tiff(str(dest))
    assert int(tifftools.Tag.ImageDescription) not in info['ifds'][0]['tags']
    tifftools.tiff_set(dest, overwrite=True, setlist=[('ImageDescription', 'Dog digging')])
    info = tifftools.read_tiff(str(dest))
    assert info['ifds'][0]['tags'][int(tifftools.Tag.ImageDescription)]['data'] == 'Dog digging'


def test_tiff_set_stdin(tmp_path, monkeypatch):
    mock_stdin = io.BytesIO()
    mock_stdin.write(b'Dog digging')
    mock_stdin.seek(0)
    mock_stdin.seekable = lambda: False

    class Namespace(object):
        pass

    mock_obj = Namespace()
    mock_obj.buffer = mock_stdin
    monkeypatch.setattr('sys.stdin', mock_obj)

    path = datastore.fetch('d043-200.tif')
    dest = tmp_path / 'results.tif'
    tifftools.tiff_set(str(path), dest, setlist=[('ImageDescription', '@-')])
    info = tifftools.read_tiff(str(dest))
    assert info['ifds'][0]['tags'][int(tifftools.Tag.ImageDescription)]['data'] == 'Dog digging'


def test_tiff_set_fromfile(tmp_path):
    path = datastore.fetch('d043-200.tif')
    dest = tmp_path / 'results.tif'
    tagfile = tmp_path / 'tag.txt'
    with open(tagfile, 'w') as fptr:
        fptr.write('Dog digging')
    tifftools.tiff_set(str(path), dest, setlist=[('ImageDescription', '@%s' % tagfile)])
    info = tifftools.read_tiff(str(dest))
    assert info['ifds'][0]['tags'][int(tifftools.Tag.ImageDescription)]['data'] == 'Dog digging'


@pytest.mark.parametrize('setlist,msg', [
    ([('Orientation:LONG', 'notanumber')], 'cannot be converted'),
    ([('Orientation:BYTE', '-2')], 'cannot be converted'),
    ([('Orientation:ASCII', b'\xff\x00')], 'cannot be converted'),
    ([('Orientation:BYTE', '3,4.2')], 'cannot be converted'),
    ([('Orientation:BYTE', '256')], 'cannot be converted'),
    ([('Orientation:DOUBLE', '5.4,notanumber')], 'cannot be converted'),
    ([('Orientation:BADTYPE', '1')], 'Unknown datatype'),
])
def test_tiff_set_failures(tmp_path, setlist, msg):
    path = datastore.fetch('d043-200.tif')
    dest = tmp_path / 'results.tif'
    with pytest.raises(Exception) as exc:
        tifftools.tiff_set(path, dest, setlist=setlist)
    assert msg in str(exc.value)


@pytest.mark.parametrize('setlist,msg', [
    ([('Orientation:LONG', 9)], 'not in known values'),
    ([('Orientation', None)], 'Could not determine data'),
])
def test_tiff_set_warnings(tmp_path, setlist, msg, caplog):
    path = datastore.fetch('d043-200.tif')
    dest = tmp_path / 'results.tif'
    with caplog.at_level(logging.WARNING):
        tifftools.tiff_set(path, dest, setlist=setlist)
    assert msg in caplog.text


def test_tiff_set_setfrom_missing(tmp_path, caplog):
    path = datastore.fetch('d043-200.tif')
    dest = tmp_path / 'results.tif'
    with caplog.at_level(logging.WARNING):
        tifftools.tiff_set(str(path) + ',1', dest, setfrom=[('InkNames', path)])
    assert 'is not in' in caplog.text
