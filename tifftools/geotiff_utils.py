# flake8: noqa 501

from .constants import Datatype, Tag, TiffConstantSet, TiffTag

# These aren't tiff tags; these are GeoTIFF GeoKey values.
GeoTiffGeoKey = TiffConstantSet(TiffTag, {
    1024: {'name': 'GTModelType', 'altnames': {'GTModelTypeGeoKey'}, 'datatype': Datatype.DOUBLE},
    1025: {'name': 'GTRasterType', 'altnames': {'GTRasterTypeGeoKey'}, 'datatype': Datatype.DOUBLE},
    1026: {'name': 'GTCitation', 'altnames': {'GTCitationGeoKey'}, 'datatype': Datatype.ASCII},
    2048: {'name': 'GeographicType', 'altnames': {'GeographicTypeGeoKey'}, 'datatype': Datatype.DOUBLE},
    2049: {'name': 'GeogCitation', 'altnames': {'GeogCitationGeoKey'}, 'datatype': Datatype.ASCII},
    2050: {'name': 'GeogGeodeticDatum', 'altnames': {'GeogGeodeticDatumGeoKey'}, 'datatype': Datatype.DOUBLE},
    2051: {'name': 'GeogPrimeMeridian', 'altnames': {'GeogPrimeMeridianGeoKey'}, 'datatype': Datatype.DOUBLE},
    2052: {'name': 'GeogLinearUnits', 'altnames': {'GeogLinearUnitsGeoKey'}, 'datatype': Datatype.DOUBLE},
    2053: {'name': 'GeogLinearUnitSize', 'altnames': {'GeogLinearUnitSizeGeoKey'}, 'datatype': Datatype.DOUBLE},
    2054: {'name': 'GeogAngularUnits', 'altnames': {'GeogAngularUnitsGeoKey'}, 'datatype': Datatype.DOUBLE},
    2055: {'name': 'GeogAngularUnitSize', 'altnames': {'GeogAngularUnitSizeGeoKey'}, 'datatype': Datatype.DOUBLE},
    2056: {'name': 'GeogEllipsoid', 'altnames': {'GeogEllipsoidGeoKey'}, 'datatype': Datatype.DOUBLE},
    2057: {'name': 'GeogSemiMajorAxis', 'altnames': {'GeogSemiMajorAxisGeoKey'}, 'datatype': Datatype.DOUBLE},
    2058: {'name': 'GeogSemiMinorAxis', 'altnames': {'GeogSemiMinorAxisGeoKey'}, 'datatype': Datatype.DOUBLE},
    2059: {'name': 'GeogInvFlattening', 'altnames': {'GeogInvFlatteningGeoKey'}, 'datatype': Datatype.DOUBLE},
    2060: {'name': 'GeogAzimuthUnits', 'altnames': {'GeogAzimuthUnitsGeoKey'}, 'datatype': Datatype.DOUBLE},
    2061: {'name': 'GeogPrimeMeridianLong', 'altnames': {'GeogPrimeMeridianLongGeoKey'}, 'datatype': Datatype.DOUBLE},
    2062: {'name': 'GeogTOWGS84', 'altnames': {'GeogTOWGS84GeoKey'}, 'datatype': Datatype.DOUBLE},
    3072: {'name': 'ProjectedCSType', 'altnames': {'ProjectedCSTypeGeoKey'}, 'datatype': Datatype.DOUBLE},
    3073: {'name': 'PCSCitation', 'altnames': {'PCSCitationGeoKey'}, 'datatype': Datatype.ASCII},
    3074: {'name': 'Projection', 'altnames': {'ProjectionGeoKey'}, 'datatype': Datatype.DOUBLE},
    3075: {'name': 'ProjCoordTrans', 'altnames': {'ProjCoordTransGeoKey'}, 'datatype': Datatype.DOUBLE},
    3076: {'name': 'ProjLinearUnits', 'altnames': {'ProjLinearUnitsGeoKey'}, 'datatype': Datatype.DOUBLE},
    3077: {'name': 'ProjLinearUnitSize', 'altnames': {'ProjLinearUnitSizeGeoKey'}, 'datatype': Datatype.DOUBLE},
    3078: {'name': 'ProjStdParallel1', 'altnames': {'ProjStdParallel1GeoKey', 'ProjStdParallel', 'ProjStdParallelGeoKey'}, 'datatype': Datatype.DOUBLE},
    3079: {'name': 'ProjStdParallel2', 'altnames': {'ProjStdParallel2GeoKey'}, 'datatype': Datatype.DOUBLE},
    3080: {'name': 'ProjNatOriginLong', 'altnames': {'ProjNatOriginLongGeoKey', 'ProjOriginLong', 'ProjOriginLongGeoKey'}, 'datatype': Datatype.DOUBLE},
    3081: {'name': 'ProjNatOriginLat', 'altnames': {'ProjNatOriginLatGeoKey', 'ProjOriginLat', 'ProjOriginLatGeoKey'}, 'datatype': Datatype.DOUBLE},
    3082: {'name': 'ProjFalseEasting', 'altnames': {'ProjFalseEastingGeoKey'}, 'datatype': Datatype.DOUBLE},
    3083: {'name': 'ProjFalseNorthing', 'altnames': {'ProjFalseNorthingGeoKey'}, 'datatype': Datatype.DOUBLE},
    3084: {'name': 'ProjFalseOriginLong', 'altnames': {'ProjFalseOriginLongGeoKey'}, 'datatype': Datatype.DOUBLE},
    3085: {'name': 'ProjFalseOriginLat', 'altnames': {'ProjFalseOriginLatGeoKey'}, 'datatype': Datatype.DOUBLE},
    3086: {'name': 'ProjFalseOriginEasting', 'altnames': {'ProjFalseOriginEastingGeoKey'}, 'datatype': Datatype.DOUBLE},
    3087: {'name': 'ProjFalseOriginNorthing', 'altnames': {'ProjFalseOriginNorthingGeoKey'}, 'datatype': Datatype.DOUBLE},
    3088: {'name': 'ProjCenterLong', 'altnames': {'ProjCenterLongGeoKey'}, 'datatype': Datatype.DOUBLE},
    3089: {'name': 'ProjCenterLat', 'altnames': {'ProjCenterLatGeoKey'}, 'datatype': Datatype.DOUBLE},
    3090: {'name': 'ProjCenterEasting', 'altnames': {'ProjCenterEastingGeoKey'}, 'datatype': Datatype.DOUBLE},
    3091: {'name': 'ProjCenterNorthing', 'altnames': {'ProjCenterNorthingGeoKey'}, 'datatype': Datatype.DOUBLE},
    3092: {'name': 'ProjScaleAtNatOrigin', 'altnames': {'ProjScaleAtNatOriginGeoKey', 'ProjScaleAtOrigin', 'ProjScaleAtOriginGeoKey'}, 'datatype': Datatype.DOUBLE},
    3093: {'name': 'ProjScaleAtCenter', 'altnames': {'ProjScaleAtCenterGeoKey'}, 'datatype': Datatype.DOUBLE},
    3094: {'name': 'ProjAzimuthAngle', 'altnames': {'ProjAzimuthAngleGeoKey'}, 'datatype': Datatype.DOUBLE},
    3095: {'name': 'ProjStraightVertPoleLong', 'altnames': {'ProjStraightVertPoleLongGeoKey'}, 'datatype': Datatype.DOUBLE},
    3096: {'name': 'ProjRectifiedGridAngle', 'altnames': {'ProjRectifiedGridAngleGeoKey'}, 'datatype': Datatype.DOUBLE},
    4096: {'name': 'VerticalCSType', 'altnames': {'VerticalCSTypeGeoKey'}, 'datatype': Datatype.DOUBLE},
    4097: {'name': 'VerticalCitation', 'altnames': {'VerticalCitationGeoKey'}, 'datatype': Datatype.ASCII},
    4098: {'name': 'VerticalDatum', 'altnames': {'VerticalDatumGeoKey'}, 'datatype': Datatype.DOUBLE},
    4099: {'name': 'VerticalUnits', 'altnames': {'VerticalUnitsGeoKey'}, 'datatype': Datatype.DOUBLE},
    5120: {'name': 'CoordinateEpoch', 'altnames': {'CoordinateEpochGeoKey'}, 'datatype': Datatype.DOUBLE},
})


def GeoKeysToDict(keys, ifd, dest=None, linePrefix=''):
    """
    Convert the GeoKeys list of values into a dictionary.

    :param keys: the list of values from the GeoKeyDirectoryTag.  This is a
        multiple of four values where the first 3 values are a version tuple
        and the fourth value is the number of 4-tuples in the rest of the list.
        Each further set of 4 values is (0) a key id from GeoTiffGeoKey, (1)
        either a 0 to indicate there is exactly one short value stored in the
        last element of the tuple, or the value of GeoDoubleParamsTag or
        GeoAsciiParamsTag, (2) the number of values used for this tag.  For
        ASCII values this is the number of characters, (3) either a short
        value or the offset in the list of doubles or characters in
        GeoDoubleParamsTag or GeoAsciiParamsTag.
    :param ifd: the parent ifd.  Used to parse GeoDoubleParamsTag and
        GeoAsciiParamsTag.
    :param dest: if not None, output results in a pretty-printed format to
        this stream.
    :param linePrefix: if dest is not None, prefix each line of output with
        this string.
    """
    result = {}
    if tuple(keys[:3]) not in {(1, 1, 0), (1, 1, 1)} or keys[3] * 4 + 4 != len(keys):
        return result
    doubles = (ifd['tags'][Tag.GeoDoubleParamsTag.value]['data']
               if Tag.GeoDoubleParamsTag.value in ifd['tags'] else [])
    asciis = (ifd['tags'][Tag.GeoAsciiParamsTag.value]['data']
              if Tag.GeoAsciiParamsTag.value in ifd['tags'] else '')
    for idx in range(4, len(keys), 4):
        keyid, tagval, count, offset = keys[idx:idx + 4]
        name = GeoTiffGeoKey[keyid].name
        if not tagval:
            result[name] = [offset]
        elif tagval == Tag.GeoDoubleParamsTag.value:
            result[name] = doubles[offset:offset + count]
        elif tagval == Tag.GeoAsciiParamsTag.value:
            val = asciis[offset:offset + count]
            result[name] = val[:-1] if val[-1:] == '|' else val
    if dest:
        for key, value in result.items():
            dest.write('\n%s%s: %s' % (
                linePrefix, key, value
                if isinstance(value, str) else
                ' '.join(str(v) for v in value)))
    return result


def dictToGeoKeys(geoDict, tagsDict):
    doubles = []
    asciis = ''
    geokeys = [[1, 1, 1, 0]]
    for key, value in geoDict.items():
        key = GeoTiffGeoKey[key].value if key in GeoTiffGeoKey else int(key)
        if key in GeoTiffGeoKey and GeoTiffGeoKey[key].datatype == Datatype.ASCII:
            datatype = Tag.GeoAsciiParamsTag.value
            datalen = len(value)
            dataval = len(asciis)
            asciis += value + '|'
        else:
            if not isinstance(value, (list, tuple)):
                value = [value]
            if len(value) == 1 and -32768 <= value[0] <= 32767 and value[0] == int(value[0]):
                datatype = 0
                datalen = 1
                dataval = int(value[0])
            else:
                datatype = Tag.GeoDoubleParamsTag.value
                datalen = len(value)
                dataval = len(doubles)
                doubles += [float(v) for v in value]
        geokeys.append([key, datatype, datalen, dataval])
    geokeys[0][3] = len(geokeys) - 1
    geokeys = [v for geokey in sorted(geokeys) for v in geokey]
    tagsDict[Tag.GeoKeyDirectoryTag.value] = {
        'datatype': Datatype.SHORT,
        'data': geokeys,
    }
    if len(doubles):
        tagsDict[Tag.GeoDoubleParamsTag.value] = {
            'datatype': Datatype.DOUBLE,
            'data': doubles,
        }
    if len(asciis):
        tagsDict[Tag.GeoAsciiParamsTag.value] = {
            'datatype': Datatype.ASCII,
            'data': asciis,
        }


Tag.GeoKeyDirectoryTag.__dict__.update({
    'dump': lambda *args: GeoKeysToDict(*args) and '',
    'dumpraw': GeoKeysToDict,
})
