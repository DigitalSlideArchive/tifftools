import shutil

import pytest

import tifftools

from .datastore import datastore


@pytest.mark.parametrize('setlist,ifdspec,tag,datavalue', [
    ([('ImageDescription', 'Dog digging')], '', tifftools.Tag.ImageDescription, 'Dog digging'),
    ([('Orientation', '2')], '', tifftools.Tag.Orientation, [2]),
    ([('FNumber,0,EXIFIFD:0', '54,10')], ',0,EXIFIFD:0',
     tifftools.constants.EXIFTag.FNumber, [54, 10]),
    ([('FNumber,0,EXIFIFD:0', '0x36,0x0000A')], ',0,EXIFIFD:0',
     tifftools.constants.EXIFTag.FNumber, [54, 10]),
    ([('FNumber:DOUBLE,0,EXIFIFD:0', '5.4')], ',0,EXIFIFD:0',
     tifftools.constants.EXIFTag.FNumber, [5.4]),
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
    with pytest.raises(Exception):
        tifftools.tiff_set(dest, setlist=[('ImageDescription', 'Dog digging')])
    info = tifftools.read_tiff(str(dest))
    assert int(tifftools.Tag.ImageDescription) not in info['ifds'][0]['tags']
    tifftools.tiff_set(dest, overwrite=True, setlist=[('ImageDescription', 'Dog digging')])
    info = tifftools.read_tiff(str(dest))
    assert info['ifds'][0]['tags'][int(tifftools.Tag.ImageDescription)]['data'] == 'Dog digging'
