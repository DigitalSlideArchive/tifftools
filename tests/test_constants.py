import pytest

import tifftools
from tifftools.constants import get_or_create_tag


def test_tiffconstant():
    c = tifftools.Tag.ImageDescription
    assert 'name' in c
    assert c.name == 'ImageDescription'
    assert c['name'] == 'ImageDescription'
    assert c.value == 270
    assert int(c) == 270
    assert 'notpresent' not in c
    assert 270 == c
    assert '270' == c
    assert '0x10e' == c
    assert 'ImageDescription' == c
    assert str(c) == 'ImageDescription 270 (0x10E)'
    d = tifftools.constants.TiffConstant(270, {'name': 'Different'})
    assert d != c
    e = tifftools.constants.TiffConstant(270, {'name': 'ImageDescription'})
    assert e == c
    with pytest.raises(KeyError):
        c['notpresent']


def test_tiffconstantset():
    s = tifftools.Tag
    assert 270 in s
    assert 'ImageDescription' in s
    assert 'imagedescription' in s
    assert 'IMAGEDESCRIPTION' in s
    assert 'notpresent' not in s
    assert s[270].name == 'ImageDescription'
    assert s['270'].name == 'ImageDescription'
    assert '270' in s
    assert '0x10e' in s
    assert s.ImageDescription == 270
    assert s.imagedescription == 270
    assert s.IMAGEDESCRIPTION == 270
    assert s['ImageDescription'] == 270
    assert s['imagedescription'] == 270
    assert s['IMAGEDESCRIPTION'] == 270
    assert getattr(s, '270').name == 'ImageDescription'
    assert getattr(s, '0x10e').name == 'ImageDescription'
    with pytest.raises(KeyError):
        s['notpresent']
    assert s.get('ImageDescription').name == 'ImageDescription'
    assert s.get('notpresent') is None


def test_tiffconstant_property():
    c = tifftools.Tag.ImageDescription
    assert c.isIFD() is False
    assert not isinstance(c.datatype, tuple)
    c = tifftools.Tag.SubIFD
    assert c.isIFD() is True
    assert isinstance(c.datatype, tuple)


def test_get_or_create_tag():
    assert get_or_create_tag('ImageDescription', tifftools.Tag).name == 'ImageDescription'
    assert get_or_create_tag(
        tifftools.Tag.ImageDescription, tifftools.Tag).name == 'ImageDescription'
    assert get_or_create_tag('40000', tifftools.Tag).name == '40000'
    assert get_or_create_tag(40000, tifftools.Tag).name == '40000'
    assert get_or_create_tag('0x9c40', tifftools.Tag).name == '40000'
    assert isinstance(get_or_create_tag(40000, tifftools.Tag), tifftools.TiffTag)
    assert get_or_create_tag(40000, tifftools.Tag).get('datatype') is None
    assert get_or_create_tag(
        40000, tifftools.Tag, datatype=tifftools.Datatype.ASCII
    ).datatype == tifftools.Datatype.ASCII
    assert get_or_create_tag(40000).name == '40000'
    assert isinstance(get_or_create_tag(40000), tifftools.TiffTag)


def test_get_or_create_tag_limits():
    with pytest.raises(tifftools.exceptions.UnknownTagError):
        get_or_create_tag(-1)
    with pytest.raises(tifftools.exceptions.UnknownTagError):
        get_or_create_tag(70000)
    with pytest.raises(tifftools.exceptions.UnknownTagError):
        get_or_create_tag('notatag')
    get_or_create_tag(70000, upperLimit=False)
