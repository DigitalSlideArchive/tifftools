import tifftools


def test_tiffconstant():
    c = tifftools.Tag.ImageDescription
    assert 'name' in c
    assert c.name == 'ImageDescription'
    assert c['name'] == 'ImageDescription'
    assert c.value == 270
    assert int(c) == 270
    assert 'notpresent' not in c
    assert 270 == c
    assert 'ImageDescription' == c
    assert str(c) == 'ImageDescription 270 (0x10E)'
    d = tifftools.constants.TiffConstant(270, {'name': 'Different'})
    assert d != c
    e = tifftools.constants.TiffConstant(270, {'name': 'ImageDescription'})
    assert e == c


def test_tiffconstantset():
    s = tifftools.Tag
    assert 270 in s
    assert 'ImageDescription' in s
    assert 'imagedescription' in s
    assert 'notpresent' not in s
    assert s[270].name == 'ImageDescription'
    assert s.ImageDescription == 270
