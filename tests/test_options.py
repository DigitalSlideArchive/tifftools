import pytest

import tifftools

from .datastore import datastore


@pytest.mark.parametrize('bigtiff', [[], ['-8'], ['-4']])
@pytest.mark.parametrize('bigendian', [[], ['-B'], ['-L']])
def test_bigtiff_bigendian(tmp_path, bigtiff, bigendian):
    path = datastore.fetch('d043-200.tif')
    dest = tmp_path / 'results.tif'
    cmd = ['merge', path, str(dest)]
    cmd.extend(bigtiff)
    cmd.extend(bigendian)
    tifftools.main(cmd)
    srcinfo = tifftools.read_tiff(path)
    destinfo = tifftools.read_tiff(dest)
    srcval = srcinfo['ifds'][0]['tags'][int(tifftools.Tag.EXIFIFD)]['ifds'][0][0]['tags'][
        int(tifftools.constants.EXIFTag.MakerNote)]['data']
    destval = destinfo['ifds'][0]['tags'][int(tifftools.Tag.EXIFIFD)]['ifds'][0][0]['tags'][
        int(tifftools.constants.EXIFTag.MakerNote)]['data']
    assert srcval == destval
