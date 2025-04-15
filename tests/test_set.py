import io
import logging
import shutil

import pytest

import tifftools

from .datastore import datastore

LOGGER = logging.getLogger('tifftools')


@pytest.mark.parametrize(('setlist', 'ifdspec', 'tag', 'datavalue'), [
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


@pytest.mark.parametrize(('unsetlist', 'ifdspec', 'tag'), [
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

    class Namespace:
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


@pytest.mark.parametrize(('setlist', 'msg'), [
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


@pytest.mark.parametrize(('setlist', 'msg'), [
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


def test_tiff_set_projection_and_gcps_with_pyproj(tmp_path):
    expect_import_error = False
    try:
        import pyproj  # noqa: F401
    except ImportError:
        expect_import_error = True

    path = datastore.fetch('d043-200.tif')
    dest = tmp_path / 'results.tif'
    projection = (
        '+proj=aea +lat_0=23 +lon_0=-96 +lat_1=29.5 +lat_2=45.5'
        ' +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs'
    )
    gcps = [
        (1979142.78, 2368597.47, 0, 0),
        (2055086.35, 2449556.39, 100, 100),
    ]
    if expect_import_error:
        with pytest.raises(tifftools.TifftoolsError):
            tifftools.tiff_set(str(path), dest, setlist=[
                ('projection', projection),
                ('gcps', gcps),
            ])
    else:
        tifftools.tiff_set(str(path), dest, setlist=[
            ('projection', projection),
            ('gcps', gcps),
        ])
        info = tifftools.read_tiff(str(dest))
        assert info['ifds'][0]['tags'][int(tifftools.Tag.GeoKeyDirectoryTag)]['data'] == [
            1, 1, 0, 13, 1024, 0, 1, 1,
            1025, 0, 1, 1, 2049, 34737, 1, 0,
            2054, 0, 1, 9102, 2057, 34736, 1, 0,
            2059, 34736, 1, 1, 3078, 34736, 1, 2,
            3079, 34736, 1, 3, 3081, 34736, 1, 4,
            3080, 34736, 1, 5, 1026, 34737, 1, 1,
            3075, 0, 1, 11, 3076, 0, 1, 9001,
        ]
        assert info['ifds'][0]['tags'][int(tifftools.Tag.GeoDoubleParamsTag)]['data'] == [
            6378137.0, 298.257223563, 29.5, 45.5, 23.0, -96.0,
        ]
        assert info['ifds'][0]['tags'][int(tifftools.Tag.GeoAsciiParamsTag)
                                       ]['data'] == 'WGS84|Albers Equal Area'
        assert info['ifds'][0]['tags'][int(tifftools.Tag.ModelTiePointTag)]['data'] == [
            0.0, 0.0, 0.0, 1979142.78, 2368597.47, 0.0,
            100.0, 100.0, 0.0, 2055086.35, 2449556.39, 0.0,
        ]


@pytest.mark.parametrize('method', ['direct', 'tiff_set', 'main'])
def test_tiff_set_projection_and_gcps_without_pyproj(tmp_path, method):
    path = datastore.fetch('d043-200.tif')
    dest = tmp_path / 'results.tif'
    projection = 'epsg:4326'
    gcps = [(-77.05, 38.88, 0, 0), (-77.04, 38.89, 100, 100)]
    if method == 'direct':
        tifftools.commands.set_gcps(str(path), gcps, output=str(dest), overwrite=True)
        tifftools.commands.set_projection(str(path), projection, output=str(dest), overwrite=True)
    elif method == 'tiff_set':
        tifftools.tiff_set(str(path), dest, setlist=[
            ('projection', projection),
            ('gcps', gcps),
        ])
    elif method == 'main':
        tifftools.main([
            'set', str(path), str(dest),
            '--set', 'projection', projection,
            '--set', 'gcps', ' '.join(' '.join(str(g) for g in gcp) for gcp in gcps),
        ])
    info = tifftools.read_tiff(str(dest))
    assert info['ifds'][0]['tags'][int(tifftools.Tag.GeoKeyDirectoryTag)]['data'] == [
        1, 1, 0, 3, 1024, 0, 1, 2, 1025, 0, 1, 1, 2048, 0, 1, 4326,
    ]


def test_tiff_set_projection_edge_case(tmp_path):
    try:
        path = datastore.fetch('d043-200.tif')
        result = tifftools.commands._set_projection(
            path, '+proj=longlat +axis=esu',
        )
        assert result == [
            (
                'GeoKeyDirectoryTag',
                ('1 1 0 6 1024 0 1 2 1025 0 1 1 2049 34737 1 0 '
                 '2054 0 1 9102 2057 34736 1 0 2059 34736 1 1'),
            ),
            ('GeoDoubleParamsTag', '6378137.0 298.257223563'),
            ('GeoAsciiParamsTag', 'WGS84'),
        ]
    except tifftools.TifftoolsError:
        # pyproj not installed
        pass
