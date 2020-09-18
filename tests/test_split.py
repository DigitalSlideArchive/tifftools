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
