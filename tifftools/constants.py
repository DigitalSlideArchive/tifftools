# flake8: noqa: E501
# Disable flake8 line-length check (E501), it makes this file harder to read

import struct

from .exceptions import UnknownTagError


class TiffConstant(int):
    def __new__(cls, value, *args, **kwargs):
        return super().__new__(cls, value)

    def __init__(self, value, constantDict):
        """
        Create a constant.  The constant is at least a value and an
        associated name.  It can have other properties.

        :param value: an integer.
        :param constantDict: a dictionary with at least a 'name' key.
        """
        self.__dict__.update(constantDict)
        self.value = value
        self.name = str(getattr(self, 'name', self.value))

    def __str__(self):
        if str(self.name) != str(self.value):
            return '%s %d (0x%X)' % (self.name, self.value, self.value)
        return '%d (0x%X)' % (self.value, self.value)

    def __getitem__(self, key):
        try:
            return getattr(self, str(key))
        except AttributeError:
            raise KeyError(key)

    def __int__(self):
        return self.value

    def __eq__(self, other):
        if isinstance(other, TiffConstant):
            return self.value == other.value and self.name == other.name
        try:
            intOther = int(other)
            return self.value == intOther
        except ValueError:
            try:
                intOther = int(other, 0)
                return self.value == intOther
            except ValueError:
                pass
        except TypeError:
            return False
        return self.name.upper() == other.upper()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __contains__(self, other):
        return hasattr(self, str(other))

    def __hash__(self):
        return hash((type(self).__name__, self.value))

    def get(self, key, default=None):
        return getattr(self, str(key), default)


class TiffTag(TiffConstant):
    def isOffsetData(self):
        return 'bytecounts' in self

    def isIFD(self):
        datatypes = self.get('datatype', None)
        if not isinstance(datatypes, tuple):
            return datatypes == Datatype.IFD or datatypes == Datatype.IFD8
        return Datatype.IFD in datatypes or Datatype.IFD8 in datatypes


class TiffConstantSet:
    def __init__(self, setNameOrClass, setDict):
        """
        Create a set of TiffConstant values.

        :param setNameOrClass: the set name or class; this is the class name
            for the constants.  If a class, this must be a subclass of
            TiffConstant.
        :param setDict: a dictionary to turn into TiffConstant values.  The
            keys should be integers and the values dictionaries with at least a
            name key.
        """
        if isinstance(setNameOrClass, str):
            setClass = type(setNameOrClass, (TiffConstant,), {})
            globals()[setNameOrClass] = setClass
        else:
            setClass = setNameOrClass
        entries = {}
        names = {}
        for k, v in setDict.items():
            entry = setClass(k, v)
            entries[k] = entry
            names[entry.name.upper()] = entry
            names[str(int(entry))] = entry
            if 'altnames' in v:
                for altname in v['altnames']:
                    names[altname.upper()] = entry
        self.__dict__.update(names)
        self._entries = entries
        self._setClass = setClass

    def __contains__(self, other):
        return hasattr(self, str(other))

    def __getattr__(self, key):
        try:
            key = str(int(key, 0))
        except (ValueError, TypeError):
            pass
        try:
            return self.__dict__[key.upper()]
        except KeyError:
            raise AttributeError("'%s' object has no attribute '%s'" % (type(self).__name__, key))

    def __getitem__(self, key):
        if isinstance(key, TiffConstant):
            key = int(key)
        try:
            return getattr(self, str(key))
        except AttributeError:
            raise KeyError(key)

    def get(self, key, default=None):
        if hasattr(self, str(key)):
            return getattr(self, str(key))
        return default

    def __iter__(self):
        for _k, v in sorted(self._entries.items()):
            yield v


def get_or_create_tag(key, tagSet=None, upperLimit=True, **tagOptions):
    """
    Get a tag from a tag set.  If the key does not exist and can be converted
    to an integer, create a tag with that value of the same type as used by the
    specified tag set.  If no tag set is specified, return a TiffConstant with
    the specified value.

    :param key: the name or value of the tag to get or create.
    :param tagSet: optional TiffConstantSet with known tags.
    :param upperLimit: if True, don't allow new tags with values >= 65536.
        Such tags are used for signaling in libtiff, so this can optionally be
        allowed.
    :param **tagOptions: if tag needs to be created and this is specified, add
        this as part of creating the tag.
    :returns: a TiffConstant.
    """
    if tagSet and key in tagSet:
        return tagSet[key]
    try:
        value = int(key)
    except ValueError:
        try:
            value = int(key, 0)
        except ValueError:
            value = -1
    if tagSet and value in tagSet:
        return tagSet[value]
    if value < 0 or (upperLimit and value >= 65536):
        raise UnknownTagError('Unknown tag %s' % key)
    tagClass = tagSet._setClass if tagSet else TiffTag
    return tagClass(value, tagOptions)


Datatype = TiffConstantSet('TiffDatatype', {
    1: {'pack': 'B', 'name': 'BYTE', 'size': 1, 'desc': 'UINT8 - unsigned byte'},
    2: {'pack': None, 'name': 'ASCII', 'size': 1, 'desc': 'null-terminated string'},
    3: {'pack': 'H', 'name': 'SHORT', 'size': 2, 'desc': 'UINT16 - unsigned short'},
    4: {'pack': 'L', 'name': 'LONG', 'size': 4, 'desc': 'UINT32 - unsigned long', 'altnames': {'DWORD'}},
    5: {'pack': 'LL', 'name': 'RATIONAL', 'size': 8, 'desc': 'two UINT32 - two unsigned longs forming a numerator and a denominator'},
    6: {'pack': 'b', 'name': 'SBYTE', 'size': 1, 'desc': 'INT8 - signed byte'},
    7: {'pack': None, 'name': 'UNDEFINED', 'size': 1, 'desc': 'arbitrary binary data'},
    8: {'pack': 'h', 'name': 'SSHORT', 'size': 2, 'desc': 'INT16 - signed short'},
    9: {'pack': 'l', 'name': 'SLONG', 'size': 4, 'desc': 'INT32 - signed long'},
    10: {'pack': 'll', 'name': 'SRATIONAL', 'size': 8, 'desc': 'two INT32 - two signed longs forming a numerator and a denominator'},
    11: {'pack': 'f', 'name': 'FLOAT', 'size': 4, 'desc': 'binary32 - IEEE-754 single-precision float'},
    12: {'pack': 'd', 'name': 'DOUBLE', 'size': 8, 'desc': 'binary64 - IEEE-754 double precision float'},
    13: {'pack': 'L', 'name': 'IFD', 'size': 4, 'desc': 'UINT32 - unsigned long with the location of an Image File Directory'},
    16: {'pack': 'Q', 'name': 'LONG8', 'size': 8, 'desc': 'UINT64 - unsigned long long'},
    17: {'pack': 'q', 'name': 'SLONG8', 'size': 8, 'desc': 'INT64 - signed long long'},
    18: {'pack': 'Q', 'name': 'IFD8', 'size': 8, 'desc': 'UINT64 - unsigned long long with the location of an Image File Directory'},
})

NewSubfileType = TiffConstantSet('TiffNewSubfileType', {
    1: {'name': 'ReducedImage', 'bitfield': 1, 'desc': 'Image is a reduced-resolution version of another image in this TIFF file'},
    2: {'name': 'Page', 'bitfield': 2, 'desc': 'Image is a single page of a multi-page image'},
    4: {'name': 'Mask', 'bitfield': 4, 'desc': 'Image defines a transparency mask for another image in this TIFF file'},
    # Macro is based on Aperio's use
    8: {'name': 'Macro', 'bitfield': 8, 'desc': 'Image is an associated macro image'},
    16: {'name': 'MRC', 'bitfield': 16, 'desc': 'Mixed Raster Content'},
})

OldSubfileType = TiffConstantSet('TiffOldSubfileType', {
    1: {'name': 'Image', 'desc': 'Full-resolution image data'},
    2: {'name': 'ReducedImage', 'desc': 'Reduced-resolution image data'},
    3: {'name': 'Page', 'desc': 'A single page of a multi-page image (see the PageNumber field description'},
})

Compression = TiffConstantSet('TiffCompression', {
    1: {'name': 'None', 'desc': 'No compression, but pack data into bytes as tightly as possible leaving no unused bits except at the end of a row'},
    2: {'name': 'CCITTRLE', 'desc': 'CCITT Group 3 1-Dimensional Modified Huffman run-length encoding'},
    3: {'name': 'CCITT_T4', 'altnames': {'CCITTFAX3'}, 'desc': 'CCITT Group 3 fax encoding (T4-encoding: CCITT T.4 bi-level encoding)'},
    4: {'name': 'CCITT_T6', 'altnames': {'CCITTFAX4'}, 'desc': 'CCITT Group 4 fax encoding (T6-encoding: CCITT T.6 bi-level encoding'},
    5: {'name': 'LZW'},
    6: {'name': 'OldJPEG', 'altnames': {'OJPEG'}, 'desc': 'Pre-version 6.0 JPEG', 'lossy': True},
    7: {'name': 'JPEG', 'lossy': True},
    8: {'name': 'AdobeDeflate', 'desc': 'Adobe deflate'},
    9: {'name': 'T85', 'desc': 'TIFF/FX T.85 JBIG compression'},
    10: {'name': 'T43', 'desc': 'TIFF/FX T.43 colour by layered JBIG compression'},
    32766: {'name': 'NeXT', 'desc': 'NeXT 2-bit RLE'},
    32771: {'name': 'CCITTRLEW', 'desc': '#1 w/ word alignment'},
    32773: {'name': 'Packbits', 'desc': 'Macintosh RLE'},
    32809: {'name': 'Thunderscan', 'desc': 'ThunderScan RLE'},
    32895: {'name': 'IT8CTPad', 'desc': 'IT8 CT w/padding'},
    32896: {'name': 'IT8LW', 'desc': 'IT8 Linework RLE'},
    32897: {'name': 'IT8MP', 'desc': 'IT8 Monochrome picture'},
    32898: {'name': 'IT8BL', 'desc': 'IT8 Binary line art'},
    32908: {'name': 'PixarFilm', 'desc': 'Pixar companded 10bit LZW'},
    32909: {'name': 'PixarLog', 'desc': 'Pixar companded 11bit ZIP'},
    32946: {'name': 'Deflate', 'desc': 'Deflate compression'},
    32947: {'name': 'DCS', 'desc': 'Kodak DCS encoding'},
    33003: {'name': 'JP2kYCbCr', 'desc': 'JPEG 2000 with YCbCr format as used by Aperio', 'lossy': True},
    33004: {'name': 'JP2kLossy', 'desc': 'JPEG 2000 with lossy compression as used by Bioformats', 'lossy': True},
    33005: {'name': 'JP2kRGB', 'desc': 'JPEG 2000 with RGB format as used by Aperio', 'lossy': True},
    34661: {'name': 'JBIG', 'desc': 'ISO JBIG'},
    34676: {'name': 'SGILOG', 'desc': 'SGI Log Luminance RLE'},
    34677: {'name': 'SGILOG24', 'desc': 'SGI Log 24-bit packed'},
    34712: {'name': 'JP2000', 'desc': 'Leadtools JPEG2000', 'lossy': True},
    34887: {'name': 'LERC', 'desc': 'ESRI Lerc codec: https://github.com/Esri/lerc', 'lossy': True},
    34925: {'name': 'LZMA', 'desc': 'LZMA2'},
    50000: {'name': 'ZSTD', 'desc': 'ZSTD'},
    50001: {'name': 'WEBP', 'desc': 'WEBP', 'lossy': True},
    50002: {'name': 'JXL'},
})

Photometric = TiffConstantSet('TiffPhotometric', {
    0: {'name': 'MinIsWhite', 'desc': 'Min value is white'},
    1: {'name': 'MinIsBlack', 'desc': 'Min value is black'},
    2: {'name': 'RGB', 'desc': 'RGB color model'},
    3: {'name': 'Palette', 'desc': 'Indexed color map'},
    4: {'name': 'Mask', 'desc': 'Mask'},
    5: {'name': 'Separated', 'desc': 'Color separations'},
    6: {'name': 'YCbCr', 'desc': 'CCIR 601'},
    8: {'name': 'CIELab', 'desc': '1976 CIE L*a*b*'},
    9: {'name': 'ICCLab', 'desc': 'ICC L*a*b*'},
    10: {'name': 'ITULab', 'desc': 'ITU L*a*b*'},
    32803: {'name': 'CFA', 'desc': 'Color filter array'},
    32844: {'name': 'LogL', 'desc': 'CIE Log2(L)'},
    32845: {'name': 'LogLuv', 'desc': "CIE Log2(L) (u',v')"},
})

Thresholding = TiffConstantSet('TiffThresholding', {
    1: {'name': 'Bilevel', 'desc': 'No dithering or halftoning has been applied to the image data'},
    2: {'name': 'Halftone', 'desc': 'An ordered dither or halftone technique has been applied to the image data'},
    3: {'name': 'ErrorDiffuse', 'desc': 'A randomized process such as error diffusion has been applied to the image data'},
})

FillOrder = TiffConstantSet('TiffFillOrder', {
    1: {'name': 'MSBToLSB', 'altnames': {'MSB2LSB'}, 'desc': 'Pixels are arranged within a byte such that pixels with lower column values are stored in the higher-order bits of the byte'},
    2: {'name': 'LSBToMSB', 'altnames': {'LSB2MSB'}, 'desc': 'Pixels are arranged within a byte such that pixels with lower column values are stored in the lower-order bits of the byte'},
})

Orientation = TiffConstantSet('Orientation', {
    1: {'name': 'TopLeft', 'desc': 'Row 0 top, column 0 left'},
    2: {'name': 'TopRight', 'desc': 'Row 0 top, column 0 right'},
    3: {'name': 'BottomRight', 'altnames': {'BotRight'}, 'desc': 'Row 0 bottom, column 0 right'},
    4: {'name': 'BottomLeft', 'altnames': {'BotLeft'}, 'desc': 'Row 0 bottom, column 0 left'},
    5: {'name': 'LeftTop', 'desc': 'Row 0 left, column 0 top'},
    6: {'name': 'RightTop', 'desc': 'Row 0 right, column 0 top'},
    7: {'name': 'RightBottom', 'altnames': {'RightBot'}, 'desc': 'Row 0 right, column 0 bottom'},
    8: {'name': 'LeftBottom', 'altnames': {'LeftBot'}, 'desc': 'Row 0 left, column 0 bottom'},
})

PlanarConfig = TiffConstantSet('PlanarConfig', {
    1: {'name': 'Chunky', 'altnames': {'Contig', 'Continuous'}, 'desc': 'The component values for each pixel are stored contiguously'},
    2: {'name': 'Planar', 'altnames': {'Separate'}, 'desc': 'The components are stored in separate “component planes.'},
})

T4Options = TiffConstantSet('TiffT4Options', {
    1: {'name': '2DEncoding', 'bitfield': 1, 'desc': 'Set for two dimensional encoding'},
    2: {'name': 'Uncompressed', 'bitfield': 2, 'desc': 'Set if uncompressed mode is used'},
    4: {'name': 'FillBits', 'bitfield': 4, 'desc': 'Set if fill bits have been added'},
})

T6Options = TiffConstantSet('TiffT6Options', {
    2: {'name': 'Uncompressed', 'bitfield': 2, 'desc': 'Set if uncompressed mode is used'},
})

ResolutionUnit = TiffConstantSet('ResolutionUnit', {
    1: {'name': 'None', 'desc': 'No absolute unit of measurement'},
    2: {'name': 'Inch', 'altnames': {'in', 'inches'}},
    3: {'name': 'Centimeter', 'altnames': {'cm'}},
})

Predictor = TiffConstantSet('Predictor', {
    1: {'name': 'None', 'desc': 'No predictor'},
    2: {'name': 'Horizontal'},
    3: {'name': 'FloatingPoint'},
})

CleanFaxData = TiffConstantSet('CleanFaxData', {
    0: {'name': 'All', 'altnames': {'Clean'}},
    1: {'name': 'Regenerated', 'altnames': {'Unclean'}},
    2: {'name': 'Present'},
})

InkSet = TiffConstantSet('InkSet', {
    1: {'name': 'CMYK'},
    2: {'name': 'NotCMYK', 'altnames': {'MultiInk'}},
})

ExtraSamples = TiffConstantSet('ExtraSamples', {
    0: {'name': 'Unspecified'},
    1: {'name': 'AssociatedAlpha', 'altnames': {'AssocAlpha'}},
    2: {'name': 'UnassociatedAlpha', 'altnames': {'UnassAlpha'}},
})

SampleFormat = TiffConstantSet('SampleFormat', {
    1: {'name': 'uint', 'altnames': {'UnsignedInteger'}},
    2: {'name': 'int'},
    3: {'name': 'float', 'altnames': {'IEEEFP'}},
    4: {'name': 'Undefined', 'altnames': {'Void'}},
    5: {'name': 'ComplexInt'},
    6: {'name': 'ComplexFloat', 'altnames': {'ComplexIEEEFP'}},
})

Indexed = TiffConstantSet('Indexed', {
    0: {'name': 'NotIndexed'},
    1: {'name': 'Indexed'},
})

JPEGProc = TiffConstantSet('JPEGProc', {
    1: {'name': 'Baseline', 'altnames': {'Quant'}},
    2: {'name': 'LosslessHuffman', 'altnames': {'Huff'}},
})

JPEGLosslessPredictors = TiffConstantSet('JPEGLosslessPredictors', {
    1: {'name': 'A'},
    2: {'name': 'B'},
    3: {'name': 'C'},
    4: {'name': 'AplusBminusC'},
    5: {'name': 'AplusHalfBminusC'},
    6: {'name': 'BplusHalhAminusC'},
    7: {'name': 'HalfAplusB'},
})

YCbCrPositioning = TiffConstantSet('YCbCrPositioning', {
    1: {'name': 'Centered'},
    2: {'name': 'Cosited'},
})

EXIFTag = TiffConstantSet(TiffTag, {
    33434: {'name': 'ExposureTime', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Exposure time'},
    33437: {'name': 'FNumber', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'F number'},
    34850: {'name': 'ExposureProgram', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'Exposure program'},
    34852: {'name': 'SpectralSensitivity', 'datatype': Datatype.ASCII, 'desc': 'Spectral sensitivity'},
    34855: {'name': 'ISOSpeedRatings', 'altnames': {'PHOTOGRAPHICSENSITIVITY'}, 'datatype': Datatype.SHORT, 'desc': 'ISO speed rating'},
    34856: {'name': 'OECF', 'datatype': Datatype.UNDEFINED, 'desc': 'Optoelectric conversion factor'},
    34858: {'datatype': Datatype.SSHORT, 'name': 'TimeZoneOffset'},
    34859: {'datatype': Datatype.SHORT, 'name': 'SelfTimerMode'},
    34864: {'name': 'SensitivityType'},
    34865: {'datatype': Datatype.LONG, 'name': 'StandardOutputSensitivity'},
    34866: {'datatype': Datatype.LONG, 'name': 'RecommendedExposureIndex'},
    34867: {'name': 'ISOSPEED'},
    34868: {'name': 'ISOSPEEDLATITUDEYYY'},
    34869: {'datatype': Datatype.LONG, 'name': 'ISOSpeedLatitudezzz'},
    36864: {'name': 'ExifVersion'},
    36867: {'name': 'DateTimeOriginal', 'datatype': Datatype.ASCII, 'count': 20, 'desc': 'Date and time of original data'},
    36868: {'name': 'CreateDate', 'altnames': {'DateTimeDigitized'}, 'datatype': Datatype.ASCII},
    36873: {'name': 'GooglePlusUploadCode'},
    36880: {'datatype': Datatype.ASCII, 'name': 'OffsetTime'},
    36881: {'datatype': Datatype.ASCII, 'name': 'OffsetTimeOriginal'},
    36882: {'datatype': Datatype.ASCII, 'name': 'OffsetTimeDigitized'},
    37121: {'name': 'ComponentsConfiguration', 'datatype': Datatype.UNDEFINED, 'count': 4, 'desc': 'Meaning of each component'},
    37122: {'name': 'CompressedBitsPerPixel', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Image compression mode'},
    37377: {'name': 'ShutterSpeedValue', 'datatype': Datatype.SRATIONAL, 'count': 1, 'desc': 'Shutter speed'},
    37378: {'name': 'ApertureValue', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Aperture'},
    37379: {'name': 'BrightnessValue', 'datatype': Datatype.SRATIONAL, 'count': 1, 'desc': 'Brightness'},
    37380: {'name': 'ExposureBiasValue', 'datatype': Datatype.SRATIONAL, 'count': 1, 'desc': 'Exposure bias'},
    37381: {'name': 'MaxApertureValue', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Maximum lens aperture'},
    37382: {'name': 'SubjectDistance', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Subject distance'},
    37383: {'name': 'MeteringMode', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'Metering mode'},
    37384: {'name': 'LightSource', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'Light source'},
    37385: {'name': 'Flash', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'Flash'},
    37386: {'name': 'FocalLength', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Lens focal length'},
    37393: {'datatype': Datatype.LONG, 'name': 'ImageNumber'},
    37394: {'datatype': Datatype.ASCII, 'name': 'SecurityClassification'},
    37395: {'datatype': Datatype.ASCII, 'name': 'ImageHistory'},
    37396: {'name': 'SubjectArea', 'datatype': Datatype.SHORT, 'desc': 'Subject area'},
    37500: {'name': 'MakerNote', 'datatype': Datatype.UNDEFINED, 'desc': 'Manufacturer notes'},
    37510: {'name': 'UserComment', 'datatype': Datatype.UNDEFINED, 'desc': 'User comments'},
    37520: {'name': 'SubSecTime', 'datatype': Datatype.ASCII, 'desc': 'DateTime subseconds'},
    37521: {'name': 'SubSecTimeOriginal', 'datatype': Datatype.ASCII, 'desc': 'DateTimeOriginal subseconds'},
    37522: {'name': 'SubSecTimeDigitized', 'datatype': Datatype.ASCII, 'desc': 'DateTimeDigitized subseconds'},
    37888: {'datatype': Datatype.SRATIONAL, 'name': 'AmbientTemperature', 'altnames': {'Temperature'}},
    37889: {'datatype': Datatype.RATIONAL, 'name': 'Humidity'},
    37890: {'datatype': Datatype.RATIONAL, 'name': 'Pressure'},
    37891: {'datatype': Datatype.SRATIONAL, 'name': 'WaterDepth'},
    37892: {'datatype': Datatype.RATIONAL, 'name': 'Acceleration'},
    37893: {'datatype': Datatype.SRATIONAL, 'name': 'CameraElevationAngle'},
    40960: {'name': 'FlashpixVersion', 'datatype': Datatype.UNDEFINED, 'count': 4, 'desc': 'Supported Flashpix version'},
    40961: {'name': 'ColorSpace', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'Color space information'},
    40962: {'name': 'PixelXDimension', 'datatype': (Datatype.SHORT, Datatype.LONG), 'count': 1, 'desc': 'Valid image width'},
    40963: {'name': 'PixelYDimension', 'datatype': (Datatype.SHORT, Datatype.LONG), 'count': 1, 'desc': 'Valid image height'},
    40964: {'name': 'RelatedSoundFile', 'datatype': Datatype.ASCII, 'count': 13, 'desc': 'Related audio file'},
    41483: {'name': 'FlashEnergy', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Flash energy'},
    41484: {'name': 'SpatialFrequencyResponse', 'datatype': Datatype.UNDEFINED, 'desc': 'Spatial frequency response'},
    41486: {'name': 'FocalPlaneXResolution', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Focal plane X resolution'},
    41487: {'name': 'FocalPlaneYResolution', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Focal plane Y resolution'},
    41488: {'name': 'FocalPlaneResolutionUnit', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'Focal plane resolution unit'},
    41492: {'name': 'SubjectLocation', 'datatype': Datatype.SHORT, 'count': 2, 'desc': 'Subject location'},
    41493: {'name': 'ExposureIndex', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Exposure index'},
    41495: {'name': 'SensingMethod', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'Sensing method'},
    41728: {'name': 'FileSource', 'datatype': Datatype.UNDEFINED, 'count': 1, 'desc': 'File source'},
    41729: {'name': 'SceneType', 'datatype': Datatype.UNDEFINED, 'count': 1, 'desc': 'Scene type'},
    41730: {'name': 'CFAPattern', 'datatype': Datatype.UNDEFINED, 'desc': 'CFA pattern'},
    41985: {'name': 'CustomRendered', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'Custom image processing'},
    41986: {'name': 'ExposureMode', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'Exposure mode'},
    41987: {'name': 'WhiteBalance', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'White balance'},
    41988: {'name': 'DigitalZoomRatio', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Digital zoom ratio'},
    41989: {'name': 'FocalLengthIn35mmFilm', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'Focal length in 35 mm film'},
    41990: {'name': 'SceneCaptureType', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'Scene capture type'},
    41991: {'name': 'GainControl', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Gain control'},
    41992: {'name': 'Contrast', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'Contrast'},
    41993: {'name': 'Saturation', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'Saturation'},
    41994: {'name': 'Sharpness', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'Sharpness'},
    41995: {'name': 'DeviceSettingDescription', 'datatype': Datatype.UNDEFINED, 'desc': 'Device settings description'},
    41996: {'name': 'SubjectDistanceRange', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'Subject distance range'},
    42016: {'name': 'ImageUniqueID', 'datatype': Datatype.ASCII, 'count': 33, 'desc': 'Unique image ID'},
    42032: {'name': 'OwnerName', 'altnames': {'CAMERAOWNERNAME'}, 'datatype': Datatype.ASCII},
    42033: {'name': 'SerialNumber', 'altnames': {'BODYSERIALNUMBER'}, 'datatype': Datatype.ASCII},
    42034: {'name': 'LensInfo', 'altnames': {'LENSSPECIFICATION'}, 'datatype': Datatype.RATIONAL},
    42035: {'datatype': Datatype.ASCII, 'name': 'LensMake'},
    42036: {'datatype': Datatype.ASCII, 'name': 'LensModel'},
    42037: {'datatype': Datatype.ASCII, 'name': 'LensSerialNumber'},
    42080: {'datatype': Datatype.SHORT, 'name': 'CompositeImage'},
    42081: {'name': 'CompositeImageCount', 'altnames': {'SOURCEIMAGENUMBEROFCOMPOSITEIMAGE'}, 'datatype': Datatype.SHORT},
    42082: {'name': 'CompositeImageExposureTimes', 'altnames': {'SOURCEEXPOSURETIMESOFCOMPOSITEIMAGE'}},
    42240: {'datatype': Datatype.RATIONAL, 'name': 'Gamma'},
    59932: {'name': 'Padding'},
    59933: {'datatype': Datatype.SLONG, 'name': 'OffsetSchema'},
    65000: {'datatype': Datatype.ASCII, 'name': 'OwnerName'},
    65001: {'datatype': Datatype.ASCII, 'name': 'SerialNumber'},
    65002: {'datatype': Datatype.ASCII, 'name': 'Lens'},
    65100: {'datatype': Datatype.ASCII, 'name': 'RawFile'},
    65101: {'datatype': Datatype.ASCII, 'name': 'Converter'},
    65102: {'datatype': Datatype.ASCII, 'name': 'WhiteBalance'},
    65105: {'datatype': Datatype.ASCII, 'name': 'Exposure'},
    65106: {'datatype': Datatype.ASCII, 'name': 'Shadows'},
    65107: {'datatype': Datatype.ASCII, 'name': 'Brightness'},
    65108: {'datatype': Datatype.ASCII, 'name': 'Contrast'},
    65109: {'datatype': Datatype.ASCII, 'name': 'Saturation'},
    65110: {'datatype': Datatype.ASCII, 'name': 'Sharpness'},
    65111: {'datatype': Datatype.ASCII, 'name': 'Smoothness'},
    65112: {'datatype': Datatype.ASCII, 'name': 'MoireFilter'},
})

GPSTag = TiffConstantSet(TiffTag, {
    0: {'name': 'GPSVersionID', 'altnames': {'VersionID'}, 'datatype': Datatype.BYTE, 'count': 4, 'desc': 'GPS tag version'},
    1: {'name': 'GPSLatitudeRef', 'altnames': {'LatitudeRef'}, 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'North or South Latitude'},
    2: {'name': 'GPSLatitude', 'altnames': {'Latitude'}, 'datatype': Datatype.RATIONAL, 'count': 3, 'desc': 'Latitude'},
    3: {'name': 'GPSLongitudeRef', 'altnames': {'LongitudeRef'}, 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'East or West Longitude'},
    4: {'name': 'GPSLongitude', 'altnames': {'Longitude'}, 'datatype': Datatype.RATIONAL, 'count': 3, 'desc': 'Longitude'},
    5: {'name': 'GPSAltitudeRef', 'altnames': {'AltitudeRef'}, 'datatype': Datatype.BYTE, 'count': 1, 'desc': 'Altitude reference'},
    6: {'name': 'GPSAltitude', 'altnames': {'Altitude'}, 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Altitude'},
    7: {'name': 'GPSTimeStamp', 'altnames': {'TimeStamp'}, 'datatype': Datatype.RATIONAL, 'count': 3, 'desc': 'GPS time (atomic clock)'},
    8: {'name': 'GPSSatellites', 'altnames': {'Satellites'}, 'datatype': Datatype.ASCII, 'desc': 'GPS satellites used for measurement'},
    9: {'name': 'GPSStatus', 'altnames': {'Status'}, 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'GPS receiver status'},
    10: {'name': 'GPSMeasureMode', 'altnames': {'MeasureMode'}, 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'GPS measurement mode'},
    11: {'name': 'GPSDOP', 'altnames': {'DOP'}, 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Measurement precision'},
    12: {'name': 'GPSSpeedRef', 'altnames': {'SpeedRef'}, 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'Speed unit'},
    13: {'name': 'GPSSpeed', 'altnames': {'Speed'}, 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Speed of GPS receiver'},
    14: {'name': 'GPSTrackRef', 'altnames': {'TrackRef'}, 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'Reference for direction of movement'},
    15: {'name': 'GPSTrack', 'altnames': {'Track'}, 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Direction of movement'},
    16: {'name': 'GPSImgDirectionRef', 'altnames': {'ImgDirectionRef'}, 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'Reference for direction of image'},
    17: {'name': 'GPSImgDirection', 'altnames': {'ImgDirection'}, 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Direction of image'},
    18: {'name': 'GPSMapDatum', 'altnames': {'MapDatum'}, 'datatype': Datatype.ASCII, 'desc': 'Geodetic survey data used'},
    19: {'name': 'GPSDestLatitudeRef', 'altnames': {'DestLatitudeRef'}, 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'Reference for latitude of destination'},
    20: {'name': 'GPSDestLatitude', 'altnames': {'DestLatitude'}, 'datatype': Datatype.RATIONAL, 'count': 3, 'desc': 'Latitude of destination'},
    21: {'name': 'GPSDestLongitudeRef', 'altnames': {'DestLongitudeRef'}, 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'Reference for longitude of destination'},
    22: {'name': 'GPSDestLongitude', 'altnames': {'DestLongitude'}, 'datatype': Datatype.RATIONAL, 'count': 3, 'desc': 'Longitude of destination'},
    23: {'name': 'GPSDestBearingRef', 'altnames': {'DestBearingRef'}, 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'Reference for bearing of destination'},
    24: {'name': 'GPSDestBearing', 'altnames': {'DestBearing'}, 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Bearing of destination'},
    25: {'name': 'GPSDestDistanceRef', 'altnames': {'DestDistanceRef'}, 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'Reference for distance to destination'},
    26: {'name': 'GPSDestDistance', 'altnames': {'DestDistance'}, 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Distance to destination'},
    27: {'name': 'GPSProcessingMethod', 'altnames': {'ProcessingMethod'}, 'datatype': Datatype.UNDEFINED, 'desc': 'Name of GPS processing method'},
    28: {'name': 'GPSAreaInformation', 'altnames': {'AreaInformation'}, 'datatype': Datatype.UNDEFINED, 'desc': 'Name of GPS area'},
    29: {'name': 'GPSDateStamp', 'altnames': {'DateStamp'}, 'datatype': Datatype.ASCII, 'count': 11, 'desc': 'GPS date'},
    30: {'name': 'GPSDifferential', 'altnames': {'Differential'}, 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'GPS differential correction'},
    31: {'name': 'GPSPositioningError', 'altnames': {'PositioningError', 'GPSHPOSITIONINGERROR', 'HPOSITIONINGERROR'}, 'desc': 'Indicates horizontal positioning errors in meters'},
})

InteroperabilityTag = TiffConstantSet(TiffTag, {
    1: {'name': 'InteroperabilityIndex', 'datatype': Datatype.ASCII},
})

# These aren't tiff tags; these are GeoTIFF GeoKey values.
GeoTiffGeoKey = TiffConstantSet(TiffTag, {
    1024: {'name': 'GTModelType', 'altnames': {'GTModelTypeGeoKey'}, 'datatype': Datatype.SHORT},
    1025: {'name': 'GTRasterType', 'altnames': {'GTRasterTypeGeoKey'}, 'datatype': Datatype.SHORT},
    1026: {'name': 'GTCitation', 'altnames': {'GTCitationGeoKey'}, 'datatype': Datatype.ASCII},
    2048: {'name': 'GeographicType', 'altnames': {'GeographicTypeGeoKey'}, 'datatype': Datatype.SHORT},
    2049: {'name': 'GeogCitation', 'altnames': {'GeogCitationGeoKey'}, 'datatype': Datatype.ASCII},
    2050: {'name': 'GeogGeodeticDatum', 'altnames': {'GeogGeodeticDatumGeoKey'}, 'datatype': Datatype.SHORT},
    2051: {'name': 'GeogPrimeMeridian', 'altnames': {'GeogPrimeMeridianGeoKey'}, 'datatype': Datatype.SHORT},
    2052: {'name': 'GeogLinearUnits', 'altnames': {'GeogLinearUnitsGeoKey'}, 'datatype': Datatype.SHORT},
    2053: {'name': 'GeogLinearUnitSize', 'altnames': {'GeogLinearUnitSizeGeoKey'}, 'datatype': Datatype.DOUBLE},
    2054: {'name': 'GeogAngularUnits', 'altnames': {'GeogAngularUnitsGeoKey'}, 'datatype': Datatype.SHORT},
    2055: {'name': 'GeogAngularUnitSize', 'altnames': {'GeogAngularUnitSizeGeoKey'}, 'datatype': Datatype.DOUBLE},
    2056: {'name': 'GeogEllipsoid', 'altnames': {'GeogEllipsoidGeoKey'}, 'datatype': Datatype.SHORT},
    2057: {'name': 'GeogSemiMajorAxis', 'altnames': {'GeogSemiMajorAxisGeoKey'}, 'datatype': Datatype.DOUBLE},
    2058: {'name': 'GeogSemiMinorAxis', 'altnames': {'GeogSemiMinorAxisGeoKey'}, 'datatype': Datatype.DOUBLE},
    2059: {'name': 'GeogInvFlattening', 'altnames': {'GeogInvFlatteningGeoKey'}, 'datatype': Datatype.DOUBLE},
    2060: {'name': 'GeogAzimuthUnits', 'altnames': {'GeogAzimuthUnitsGeoKey'}, 'datatype': Datatype.SHORT},
    2061: {'name': 'GeogPrimeMeridianLong', 'altnames': {'GeogPrimeMeridianLongGeoKey'}, 'datatype': Datatype.DOUBLE},
    2062: {'name': 'GeogTOWGS84', 'altnames': {'GeogTOWGS84GeoKey'}, 'datatype': Datatype.DOUBLE},
    3072: {'name': 'ProjectedCSType', 'altnames': {'ProjectedCSTypeGeoKey'}, 'datatype': Datatype.SHORT},
    3073: {'name': 'PCSCitation', 'altnames': {'PCSCitationGeoKey'}, 'datatype': Datatype.ASCII},
    3074: {'name': 'Projection', 'altnames': {'ProjectionGeoKey'}, 'datatype': Datatype.SHORT},
    3075: {'name': 'ProjCoordTrans', 'altnames': {'ProjCoordTransGeoKey'}, 'datatype': Datatype.SHORT},
    3076: {'name': 'ProjLinearUnits', 'altnames': {'ProjLinearUnitsGeoKey'}, 'datatype': Datatype.SHORT},
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
    4096: {'name': 'VerticalCSType', 'altnames': {'VerticalCSTypeGeoKey'}, 'datatype': Datatype.SHORT},
    4097: {'name': 'VerticalCitation', 'altnames': {'VerticalCitationGeoKey'}, 'datatype': Datatype.ASCII},
    4098: {'name': 'VerticalDatum', 'altnames': {'VerticalDatumGeoKey'}, 'datatype': Datatype.SHORT},
    4099: {'name': 'VerticalUnits', 'altnames': {'VerticalUnitsGeoKey'}, 'datatype': Datatype.SHORT},
    5120: {'name': 'CoordinateEpoch', 'altnames': {'CoordinateEpochGeoKey'}, 'datatype': Datatype.DOUBLE},
})


GeoTiffCSTypes = TiffConstantSet('GeoTiffCSTypes', {
    4201: {'name': 'GCS_Adindan', 'altnames': {'Adindan'}},
    4202: {'name': 'GCS_AGD66', 'altnames': {'AGD66'}},
    4203: {'name': 'GCS_AGD84', 'altnames': {'AGD84'}},
    4204: {'name': 'GCS_Ain_el_Abd', 'altnames': {'Ain_el_Abd'}},
    4205: {'name': 'GCS_Afgooye', 'altnames': {'Afgooye'}},
    4206: {'name': 'GCS_Agadez', 'altnames': {'Agadez'}},
    4207: {'name': 'GCS_Lisbon', 'altnames': {'Lisbon'}},
    4208: {'name': 'GCS_Aratu', 'altnames': {'Aratu'}},
    4209: {'name': 'GCS_Arc_1950', 'altnames': {'Arc_1950'}},
    4210: {'name': 'GCS_Arc_1960', 'altnames': {'Arc_1960'}},
    4211: {'name': 'GCS_Batavia', 'altnames': {'Batavia'}},
    4212: {'name': 'GCS_Barbados', 'altnames': {'Barbados'}},
    4213: {'name': 'GCS_Beduaram', 'altnames': {'Beduaram'}},
    4214: {'name': 'GCS_Beijing_1954', 'altnames': {'Beijing_1954'}},
    4215: {'name': 'GCS_Belge_1950', 'altnames': {'Belge_1950'}},
    4216: {'name': 'GCS_Bermuda_1957', 'altnames': {'Bermuda_1957'}},
    4217: {'name': 'GCS_Bern_1898', 'altnames': {'Bern_1898'}},
    4218: {'name': 'GCS_Bogota', 'altnames': {'Bogota'}},
    4219: {'name': 'GCS_Bukit_Rimpah', 'altnames': {'Bukit_Rimpah'}},
    4220: {'name': 'GCS_Camacupa', 'altnames': {'Camacupa'}},
    4221: {'name': 'GCS_Campo_Inchauspe', 'altnames': {'Campo_Inchauspe'}},
    4222: {'name': 'GCS_Cape', 'altnames': {'Cape'}},
    4223: {'name': 'GCS_Carthage', 'altnames': {'Carthage'}},
    4224: {'name': 'GCS_Chua', 'altnames': {'Chua'}},
    4225: {'name': 'GCS_Corrego_Alegre', 'altnames': {'Corrego_Alegre'}},
    4226: {'name': 'GCS_Cote_d_Ivoire', 'altnames': {'Cote_d_Ivoire'}},
    4227: {'name': 'GCS_Deir_ez_Zor', 'altnames': {'Deir_ez_Zor'}},
    4228: {'name': 'GCS_Douala', 'altnames': {'Douala'}},
    4229: {'name': 'GCS_Egypt_1907', 'altnames': {'Egypt_1907'}},
    4230: {'name': 'GCS_ED50', 'altnames': {'ED50'}},
    4231: {'name': 'GCS_ED87', 'altnames': {'ED87'}},
    4232: {'name': 'GCS_Fahud', 'altnames': {'Fahud'}},
    4233: {'name': 'GCS_Gandajika_1970', 'altnames': {'Gandajika_1970'}},
    4234: {'name': 'GCS_Garoua', 'altnames': {'Garoua'}},
    4235: {'name': 'GCS_Guyane_Francaise', 'altnames': {'Guyane_Francaise'}},
    4236: {'name': 'GCS_Hu_Tzu_Shan', 'altnames': {'Hu_Tzu_Shan'}},
    4237: {'name': 'GCS_HD72', 'altnames': {'HD72'}},
    4238: {'name': 'GCS_ID74', 'altnames': {'ID74'}},
    4239: {'name': 'GCS_Indian_1954', 'altnames': {'Indian_1954'}},
    4240: {'name': 'GCS_Indian_1975', 'altnames': {'Indian_1975'}},
    4241: {'name': 'GCS_Jamaica_1875', 'altnames': {'Jamaica_1875'}},
    4242: {'name': 'GCS_JAD69', 'altnames': {'JAD69'}},
    4243: {'name': 'GCS_Kalianpur', 'altnames': {'Kalianpur'}},
    4244: {'name': 'GCS_Kandawala', 'altnames': {'Kandawala'}},
    4245: {'name': 'GCS_Kertau', 'altnames': {'Kertau'}},
    4246: {'name': 'GCS_KOC', 'altnames': {'KOC'}},
    4247: {'name': 'GCS_La_Canoa', 'altnames': {'La_Canoa'}},
    4248: {'name': 'GCS_PSAD56', 'altnames': {'PSAD56'}},
    4249: {'name': 'GCS_Lake', 'altnames': {'Lake'}},
    4250: {'name': 'GCS_Leigon', 'altnames': {'Leigon'}},
    4251: {'name': 'GCS_Liberia_1964', 'altnames': {'Liberia_1964'}},
    4252: {'name': 'GCS_Lome', 'altnames': {'Lome'}},
    4253: {'name': 'GCS_Luzon_1911', 'altnames': {'Luzon_1911'}},
    4254: {'name': 'GCS_Hito_XVIII_1963', 'altnames': {'Hito_XVIII_1963'}},
    4255: {'name': 'GCS_Herat_North', 'altnames': {'Herat_North'}},
    4256: {'name': 'GCS_Mahe_1971', 'altnames': {'Mahe_1971'}},
    4257: {'name': 'GCS_Makassar', 'altnames': {'Makassar'}},
    4258: {'name': 'GCS_EUREF89', 'altnames': {'EUREF89'}},
    4259: {'name': 'GCS_Malongo_1987', 'altnames': {'Malongo_1987'}},
    4260: {'name': 'GCS_Manoca', 'altnames': {'Manoca'}},
    4261: {'name': 'GCS_Merchich', 'altnames': {'Merchich'}},
    4262: {'name': 'GCS_Massawa', 'altnames': {'Massawa'}},
    4263: {'name': 'GCS_Minna', 'altnames': {'Minna'}},
    4264: {'name': 'GCS_Mhast', 'altnames': {'Mhast'}},
    4265: {'name': 'GCS_Monte_Mario', 'altnames': {'Monte_Mario'}},
    4266: {'name': 'GCS_M_poraloko', 'altnames': {'M_poraloko'}},
    4267: {'name': 'GCS_NAD27', 'altnames': {'NAD27'}},
    4268: {'name': 'GCS_NAD_Michigan', 'altnames': {'NAD_Michigan'}},
    4269: {'name': 'GCS_NAD83', 'altnames': {'NAD83'}},
    4270: {'name': 'GCS_Nahrwan_1967', 'altnames': {'Nahrwan_1967'}},
    4271: {'name': 'GCS_Naparima_1972', 'altnames': {'Naparima_1972'}},
    4272: {'name': 'GCS_GD49', 'altnames': {'GD49'}},
    4273: {'name': 'GCS_NGO_1948', 'altnames': {'NGO_1948'}},
    4274: {'name': 'GCS_Datum_73', 'altnames': {'Datum_73'}},
    4275: {'name': 'GCS_NTF', 'altnames': {'NTF'}},
    4276: {'name': 'GCS_NSWC_9Z_2', 'altnames': {'NSWC_9Z_2'}},
    4277: {'name': 'GCS_OSGB_1936', 'altnames': {'OSGB_1936'}},
    4278: {'name': 'GCS_OSGB70', 'altnames': {'OSGB70'}},
    4279: {'name': 'GCS_OS_SN80', 'altnames': {'OS_SN80'}},
    4280: {'name': 'GCS_Padang', 'altnames': {'Padang'}},
    4281: {'name': 'GCS_Palestine_1923', 'altnames': {'Palestine_1923'}},
    4282: {'name': 'GCS_Pointe_Noire', 'altnames': {'Pointe_Noire'}},
    4283: {'name': 'GCS_GDA94', 'altnames': {'GDA94'}},
    4284: {'name': 'GCS_Pulkovo_1942', 'altnames': {'Pulkovo_1942'}},
    4285: {'name': 'GCS_Qatar', 'altnames': {'Qatar'}},
    4286: {'name': 'GCS_Qatar_1948', 'altnames': {'Qatar_1948'}},
    4287: {'name': 'GCS_Qornoq', 'altnames': {'Qornoq'}},
    4288: {'name': 'GCS_Loma_Quintana', 'altnames': {'Loma_Quintana'}},
    4289: {'name': 'GCS_Amersfoort', 'altnames': {'Amersfoort'}},
    4290: {'name': 'GCS_RT38', 'altnames': {'RT38'}},
    4291: {'name': 'GCS_SAD69', 'altnames': {'SAD69'}},
    4292: {'name': 'GCS_Sapper_Hill_1943', 'altnames': {'Sapper_Hill_1943'}},
    4293: {'name': 'GCS_Schwarzeck', 'altnames': {'Schwarzeck'}},
    4294: {'name': 'GCS_Segora', 'altnames': {'Segora'}},
    4295: {'name': 'GCS_Serindung', 'altnames': {'Serindung'}},
    4296: {'name': 'GCS_Sudan', 'altnames': {'Sudan'}},
    4297: {'name': 'GCS_Tananarive', 'altnames': {'Tananarive'}},
    4298: {'name': 'GCS_Timbalai_1948', 'altnames': {'Timbalai_1948'}},
    4299: {'name': 'GCS_TM65', 'altnames': {'TM65'}},
    4300: {'name': 'GCS_TM75', 'altnames': {'TM75'}},
    4301: {'name': 'GCS_Tokyo', 'altnames': {'Tokyo'}},
    4302: {'name': 'GCS_Trinidad_1903', 'altnames': {'Trinidad_1903'}},
    4303: {'name': 'GCS_TC_1948', 'altnames': {'TC_1948'}},
    4304: {'name': 'GCS_Voirol_1875', 'altnames': {'Voirol_1875'}},
    4305: {'name': 'GCS_Voirol_Unifie', 'altnames': {'Voirol_Unifie'}},
    4306: {'name': 'GCS_Bern_1938', 'altnames': {'Bern_1938'}},
    4307: {'name': 'GCS_Nord_Sahara_1959', 'altnames': {'Nord_Sahara_1959'}},
    4308: {'name': 'GCS_Stockholm_1938', 'altnames': {'Stockholm_1938'}},
    4309: {'name': 'GCS_Yacare', 'altnames': {'Yacare'}},
    4310: {'name': 'GCS_Yoff', 'altnames': {'Yoff'}},
    4311: {'name': 'GCS_Zanderij', 'altnames': {'Zanderij'}},
    4312: {'name': 'GCS_MGI', 'altnames': {'MGI'}},
    4313: {'name': 'GCS_Belge_1972', 'altnames': {'Belge_1972'}},
    4314: {'name': 'GCS_DHDN', 'altnames': {'DHDN'}},
    4315: {'name': 'GCS_Conakry_1905', 'altnames': {'Conakry_1905'}},
    4322: {'name': 'GCS_WGS_72', 'altnames': {'WGS_72'}},
    4324: {'name': 'GCS_WGS_72BE', 'altnames': {'WGS_72BE'}},
    4326: {'name': 'GCS_WGS_84', 'altnames': {'WGS_84'}},
    4801: {'name': 'GCS_Bern_1898_Bern', 'altnames': {'Bern_1898_Bern'}},
    4802: {'name': 'GCS_Bogota_Bogota', 'altnames': {'Bogota_Bogota'}},
    4803: {'name': 'GCS_Lisbon_Lisbon', 'altnames': {'Lisbon_Lisbon'}},
    4804: {'name': 'GCS_Makassar_Jakarta', 'altnames': {'Makassar_Jakarta'}},
    4805: {'name': 'GCS_MGI_Ferro', 'altnames': {'MGI_Ferro'}},
    4806: {'name': 'GCS_Monte_Mario_Rome', 'altnames': {'Monte_Mario_Rome'}},
    4807: {'name': 'GCS_NTF_Paris', 'altnames': {'NTF_Paris'}},
    4808: {'name': 'GCS_Padang_Jakarta', 'altnames': {'Padang_Jakarta'}},
    4809: {'name': 'GCS_Belge_1950_Brussels', 'altnames': {'Belge_1950_Brussels'}},
    4810: {'name': 'GCS_Tananarive_Paris', 'altnames': {'Tananarive_Paris'}},
    4811: {'name': 'GCS_Voirol_1875_Paris', 'altnames': {'Voirol_1875_Paris'}},
    4812: {'name': 'GCS_Voirol_Unifie_Paris', 'altnames': {'Voirol_Unifie_Paris'}},
    4813: {'name': 'GCS_Batavia_Jakarta', 'altnames': {'Batavia_Jakarta'}},
    4901: {'name': 'GCS_ATF_Paris', 'altnames': {'ATF_Paris'}},
    4902: {'name': 'GCS_NDG_Paris', 'altnames': {'NDG_Paris'}},
    4001: {'name': 'GCSE_Airy1830', 'altnames': {'Airy1830'}},
    4002: {'name': 'GCSE_AiryModified1849', 'altnames': {'AiryModified1849'}},
    4003: {'name': 'GCSE_AustralianNationalSpheroid', 'altnames': {'AustralianNationalSpheroid'}},
    4004: {'name': 'GCSE_Bessel1841', 'altnames': {'Bessel1841'}},
    4005: {'name': 'GCSE_BesselModified', 'altnames': {'BesselModified'}},
    4006: {'name': 'GCSE_BesselNamibia', 'altnames': {'BesselNamibia'}},
    4007: {'name': 'GCSE_Clarke1858', 'altnames': {'Clarke1858'}},
    4008: {'name': 'GCSE_Clarke1866', 'altnames': {'Clarke1866'}},
    4009: {'name': 'GCSE_Clarke1866Michigan', 'altnames': {'Clarke1866Michigan'}},
    4010: {'name': 'GCSE_Clarke1880_Benoit', 'altnames': {'Clarke1880_Benoit'}},
    4011: {'name': 'GCSE_Clarke1880_IGN', 'altnames': {'Clarke1880_IGN'}},
    4012: {'name': 'GCSE_Clarke1880_RGS', 'altnames': {'Clarke1880_RGS'}},
    4013: {'name': 'GCSE_Clarke1880_Arc', 'altnames': {'Clarke1880_Arc'}},
    4014: {'name': 'GCSE_Clarke1880_SGA1922', 'altnames': {'Clarke1880_SGA1922'}},
    4015: {'name': 'GCSE_Everest1830_1937Adjustment', 'altnames': {'Everest1830_1937Adjustment'}},
    4016: {'name': 'GCSE_Everest1830_1967Definition', 'altnames': {'Everest1830_1967Definition'}},
    4017: {'name': 'GCSE_Everest1830_1975Definition', 'altnames': {'Everest1830_1975Definition'}},
    4018: {'name': 'GCSE_Everest1830Modified', 'altnames': {'Everest1830Modified'}},
    4019: {'name': 'GCSE_GRS1980', 'altnames': {'GRS1980'}},
    4020: {'name': 'GCSE_Helmert1906', 'altnames': {'Helmert1906'}},
    4021: {'name': 'GCSE_IndonesianNationalSpheroid', 'altnames': {'IndonesianNationalSpheroid'}},
    4022: {'name': 'GCSE_International1924', 'altnames': {'International1924'}},
    4023: {'name': 'GCSE_International1967', 'altnames': {'International1967'}},
    4024: {'name': 'GCSE_Krassowsky1940', 'altnames': {'Krassowsky1940'}},
    4025: {'name': 'GCSE_NWL9D', 'altnames': {'NWL9D'}},
    4026: {'name': 'GCSE_NWL10D', 'altnames': {'NWL10D'}},
    4027: {'name': 'GCSE_Plessis1817', 'altnames': {'Plessis1817'}},
    4028: {'name': 'GCSE_Struve1860', 'altnames': {'Struve1860'}},
    4029: {'name': 'GCSE_WarOffice', 'altnames': {'WarOffice'}},
    4030: {'name': 'GCSE_WGS84', 'altnames': {'WGS84'}},
    4031: {'name': 'GCSE_GEM10C', 'altnames': {'GEM10C'}},
    4032: {'name': 'GCSE_OSU86F', 'altnames': {'OSU86F'}},
    4033: {'name': 'GCSE_OSU91A', 'altnames': {'OSU91A'}},
    4034: {'name': 'GCSE_Clarke1880', 'altnames': {'Clarke1880'}},
    4035: {'name': 'GCSE_Sphere', 'altnames': {'Sphere'}},
})


GeoTiffAngularUnits = TiffConstantSet('GeoTiffAngularUnits', {
    9101: {'name': 'Angular_Radian', 'altnames': {'radian', 'rad'}},
    9102: {'name': 'Angular_Degree', 'altnames': {'degree', 'deg'}},
    9103: {'name': 'Angular_Arc_Minute', 'altnames': {'arc_minute', 'arcminute'}},
    9104: {'name': 'Angular_Arc_Second', 'altnames': {'arc_second', 'arcsecond'}},
    9105: {'name': 'Angular_Grad', 'altnames': {'grad'}},
    9106: {'name': 'Angular_Gon', 'altnames': {'gon'}},
    9107: {'name': 'Angular_DMS', 'altnames': {'dms'}},
    9108: {'name': 'Angular_DMS_Hemisphere', 'altnames': {'dms_hemisphere', 'dms_hemi'}},
})


GeoTiffLinearUnits = TiffConstantSet('GeoTiffLinearUnits', {
    9001: {'name': 'Linear_Meter', 'altnames': {'m', 'meter', 'meters'}},
    9002: {'name': 'Linear_Foot', 'altnames': {'ft', 'foot', 'feet'}},
    9003: {'name': 'Linear_Foot_US_Survey', 'altnames': {'ft_us'}},
    9004: {'name': 'Linear_Foot_Modified_American', 'altnames': {'ft_am'}},
    9005: {'name': 'Linear_Foot_Clarke', 'altnames': {'ft_cl'}},
    9006: {'name': 'Linear_Foot_Indian', 'altnames': {'ft_in'}},
    9007: {'name': 'Linear_Link', 'altnames': {'link'}},
    9008: {'name': 'Linear_Link_Benoit', 'altnames': {'link_bn'}},
    9009: {'name': 'Linear_Link_Sears', 'altnames': {'link_sr'}},
    9010: {'name': 'Linear_Chain_Benoit', 'altnames': {'chain_bn'}},
    9011: {'name': 'Linear_Chain_Sears', 'altnames': {'chain_sr'}},
    9012: {'name': 'Linear_Yard_Sears', 'altnames': {'yd_sr'}},
    9013: {'name': 'Linear_Yard_Indian', 'altnames': {'yd_in'}},
    9014: {'name': 'Linear_Fathom', 'altnames': {'fathom'}},
    9015: {'name': 'Linear_Mile_International_Nautical', 'altnames': {'kt', 'knot', 'knots', 'nmile', 'nmiles'}},
})


GeoTiffTransformations = TiffConstantSet('GeoTiffTransformations', {
    1: {'name': 'CT_TransverseMercator', 'altnames': {'TransverseMercator', 'CT_GaussBoaga', 'GaussBoaga', 'CT_GaussKruger', 'GaussKruger'}},
    2: {'name': 'CT_TransvMercator_Modified_Alaska', 'altnames': {'TransvMercator_Modified_Alaska', 'CT_AlaskaConformal', 'AlaskaConformal'}},
    3: {'name': 'CT_ObliqueMercator', 'altnames': {'ObliqueMercator', 'CT_ObliqueMercator_Hotine', 'ObliqueMercator_Hotine'}},
    4: {'name': 'CT_ObliqueMercator_Laborde', 'altnames': {'ObliqueMercator_Laborde'}},
    5: {'name': 'CT_ObliqueMercator_Rosenmund', 'altnames': {'ObliqueMercator_Rosenmund', 'CT_SwissObliqueCylindrical', 'SwissObliqueCylindrical'}},
    6: {'name': 'CT_ObliqueMercator_Spherical', 'altnames': {'ObliqueMercator_Spherical'}},
    7: {'name': 'CT_Mercator', 'altnames': {'Mercator'}},
    8: {'name': 'CT_LambertConfConic_2SP', 'altnames': {'LambertConfConic_2SP', 'CT_LambertConfConic', 'LambertConfConic'}},
    9: {'name': 'CT_LambertConfConic_1SP', 'altnames': {'LambertConfConic_1SP', 'CT_LambertConfConic_Helmert', 'LambertConfConic_Helmert'}},
    10: {'name': 'CT_LambertAzimEqualArea', 'altnames': {'LambertAzimEqualArea'}},
    11: {'name': 'CT_AlbersEqualArea', 'altnames': {'AlbersEqualArea'}},
    12: {'name': 'CT_AzimuthalEquidistant', 'altnames': {'AzimuthalEquidistant'}},
    13: {'name': 'CT_EquidistantConic', 'altnames': {'EquidistantConic'}},
    14: {'name': 'CT_Stereographic', 'altnames': {'Stereographic'}},
    15: {'name': 'CT_PolarStereographic', 'altnames': {'PolarStereographic'}},
    16: {'name': 'CT_ObliqueStereographic', 'altnames': {'ObliqueStereographic'}},
    17: {'name': 'CT_Equirectangular', 'altnames': {'Equirectangular'}},
    18: {'name': 'CT_CassiniSoldner', 'altnames': {'CassiniSoldner', 'CT_TransvEquidistCylindrical', 'TransvEquidistCylindrical'}},
    19: {'name': 'CT_Gnomonic', 'altnames': {'Gnomonic'}},
    20: {'name': 'CT_MillerCylindrical', 'altnames': {'MillerCylindrical'}},
    21: {'name': 'CT_Orthographic', 'altnames': {'Orthographic'}},
    22: {'name': 'CT_Polyconic', 'altnames': {'Polyconic'}},
    23: {'name': 'CT_Robinson', 'altnames': {'Robinson'}},
    24: {'name': 'CT_Sinusoidal', 'altnames': {'Sinusoidal'}},
    25: {'name': 'CT_VanDerGrinten', 'altnames': {'VanDerGrinten'}},
    26: {'name': 'CT_NewZealandMapGrid', 'altnames': {'NewZealandMapGrid'}},
    27: {'name': 'CT_TransvMercator_SouthOriented', 'altnames': {'CTransvMercator_SouthOriented', 'CT_SouthOrientedGaussConformal', 'SouthOrientedGaussConformal'}},
})


# from https://spatialreference.org/explorer.html
EPSGTypes = {
    'projected': [*list(range(2000, 2008)), *list(range(2009, 2036)), *list(range(2039, 2063)), *list(range(2065, 2085)), *list(range(2087, 2091)), *list(range(2093, 2139)), 2154, *list(range(2157, 2163)), 2164, 2165, 2169, *list(range(2172, 2181)), *list(range(2188, 2191)), 2193, *list(range(2195, 2199)), *list(range(2200, 2214)), *list(range(2215, 2244)), *list(range(2246, 2291)), *list(range(2294, 2297)), 2299, 2301, *list(range(2303, 2400)), *list(range(2401, 2492)), *list(range(2494, 2550)), *list(range(2551, 2577)), *list(range(2578, 2600)), *list(range(2601, 2694)), *list(range(2695, 2889)), *list(range(2891, 2934)), *list(range(2935, 2944)), *list(range(2945, 2974)), *list(range(2975, 2979)), 2980, 2981, *list(range(2985, 2989)), *list(range(2991, 3038)), *list(range(3040, 3050)), *list(range(3052, 3073)), 3074, 3075, *list(range(3077, 3103)), *list(range(3106, 3143)), 3144, 3145, 3148, 3149, *list(range(3152, 3314)), *list(range(3316, 3349)), *list(range(3350, 3356)), 3358, *list(range(3360, 3366)), *list(range(3367, 3454)), *list(range(3455, 3752)), *list(range(3753, 3774)), *list(range(3775, 3778)), *list(range(3779, 3782)), 3783, 3784, *list(range(3788, 3792)), *list(range(3793, 3803)), 3812, *list(range(3814, 3817)), *list(range(3825, 3830)), *list(range(3832, 3842)), *list(range(3844, 3853)), 3854, 3857, *list(range(3873, 3886)), *list(range(3890, 3894)), 3912, 3920, *list(range(3942, 3951)), *list(range(3968, 3971)), 3976, 3978, 3979, *list(range(3986, 3990)), *list(range(3991, 3998)), 4026, 4037, 4038, *list(range(4048, 4052)), *list(range(4056, 4064)), 4071, 4082, 4083, 4087, *list(range(4093, 4097)), 4217, *list(range(4390, 4416)), *list(range(4417, 4435)), *list(range(4437, 4440)), *list(range(4455, 4458)), 4462, 4467, 4471, *list(range(4484, 4490)), *list(range(4491, 4555)), 4559, *list(range(4568, 4590)), 4647, *list(range(4652, 4657)), *list(range(4766, 4801)), 4812, 4822, 4826, 4839, *list(range(5014, 5019)), 5041, 5042, 5048, *list(range(5069, 5073)), *list(range(5105, 5131)), *list(range(5167, 5189)), 5221, *list(range(5223, 5226)), 5234, 5235, 5243, 5247, *list(range(5253, 5260)), 5266, *list(range(5269, 5276)), *list(range(5292, 5312)), 5316, 5320, 5321, 5325, *list(range(5329, 5332)), 5337, *list(range(5343, 5350)), *list(range(5355, 5358)), 5361, 5362, 5367, 5382, 5383, 5387, 5389, 5396, 5456, 5457, *list(range(5459, 5464)), 5469, 5472, *list(range(5479, 5483)), 5490, *list(range(5513, 5517)), *list(range(5518, 5521)), 5523, 5530, 5531, *list(range(5533, 5540)), *list(range(5550, 5553)), 5559, *list(range(5562, 5570)), 5588, 5589, 5596, *list(range(5623, 5626)), 5627, 5629, *list(range(5631, 5640)), 5641, 5643, 5644, 5646, *list(range(5649, 5656)), 5659, *list(range(5663, 5681)), *list(range(5682, 5686)), 5700, 5825, 5836, 5837, 5839, 5842, 5844, 5858, *list(range(5875, 5878)), 5879, 5880, 5887, *list(range(5896, 5900)), *list(range(5921, 5941)), *list(range(6050, 6126)), 6128, 6129, 6201, 6202, 6204, 6210, 6211, *list(range(6244, 6276)), 6307, 6312, 6316, *list(range(6328, 6349)), *list(range(6350, 6357)), 6362, *list(range(6366, 6373)), *list(range(6381, 6388)), 6391, *list(range(6393, 6517)), *list(range(6518, 6604)), *list(range(6605, 6638)), 6646, *list(range(6669, 6693)), 6703, *list(range(6707, 6710)), *list(range(6720, 6724)), *list(range(6736, 6739)), *list(range(6784, 6864)), 6867, 6868, 6870, 6875, 6876, 6879, 6880, *list(range(6884, 6888)), 6915, *list(range(6922, 6926)), *list(range(6931, 6934)), 6962, 6966, 6984, 6991, *list(range(7005, 7008)), *list(range(7057, 7071)), *list(range(7074, 7082)), *list(range(7109, 7129)), 7131, 7132, 7142, *list(range(7257, 7371)), *list(range(7374, 7377)), *list(range(7528, 7646)), *list(range(7692, 7697)), *list(range(7755, 7788)), *list(range(7791, 7796)), *list(range(7799, 7802)), 7803, 7805, *list(range(7825, 7832)), *list(range(7845, 7860)), 7877, 7878, 7882, 7883, 7887, 7899, 7991, 7992, *list(range(8013, 8033)), 8035, 8036, 8044, 8045, 8058, 8059, *list(range(8065, 8069)), 8082, 8083, 8088, *list(range(8090, 8094)), *list(range(8095, 8174)), 8177, *list(range(8179, 8183)), 8184, 8185, 8187, 8189, 8191, 8193, *list(range(8196, 8199)), *list(range(8200, 8211)), *list(range(8212, 8215)), 8216, 8218, 8220, 8222, *list(range(8224, 8227)), *list(range(8311, 8349)), 8352, 8353, *list(range(8379, 8386)), 8387, 8391, 8395, 8433, 8441, 8455, 8456, *list(range(8518, 8530)), 8531, *list(range(8533, 8537)), *list(range(8538, 8541)), *list(range(8677, 8680)), 8682, 8686, 8687, 8692, 8693, 8826, *list(range(8836, 8841)), *list(range(8857, 8860)), 8903, *list(range(8908, 8911)), 8950, 8951, 9039, 9040, 9141, 9149, 9150, *list(range(9154, 9160)), 9191, *list(range(9205, 9219)), 9221, 9222, 9249, 9250, 9252, 9254, 9265, *list(range(9271, 9274)), 9284, 9285, *list(range(9295, 9298)), 9300, 9311, 9354, *list(range(9356, 9361)), 9367, 9373, 9377, 9387, 9391, *list(range(9404, 9408)), 9456, 9473, *list(range(9476, 9483)), *list(range(9487, 9495)), 9498, 9549, 9674, 9678, 9680, *list(range(9697, 9700)), 9709, 9712, 9713, 9716, 9741, 9748, 9749, 9761, 9766, 9793, 9794, *list(range(9821, 9866)), 9869, 9874, 9875, 9880, 9895, 9943, 9945, 9947, 9967, 9972, 9977, 10160, 10183, 10188, 10194, 10199, 10207, 10212, 10217, 10222, 10227, 10235, 10240, 10250, 10254, 10258, 10262, 10266, 10270, 10275, 10280, *list(range(10285, 10292)), 10306, *list(range(10314, 10318)), 10329, *list(range(10448, 10466)), 10471, 10477, 10481, 10516, 10592, 10594, 10596, 10598, 10601, 10603, 10622, 10626, 10632, 10641, 10665, 10674, 10699, 10702, *list(range(10726, 10730)), *list(range(10731, 10734)), 10744, 10745, 10759, 10773, 10801, 10802, 10820, *list(range(11114, 11119)), 20002, *list(range(20004, 20033)), 20042, *list(range(20047, 20051)), *list(range(20135, 20139)), *list(range(20249, 20259)), *list(range(20349, 20357)), *list(range(20436, 20441)), 20499, 20538, 20539, 20790, 20791, *list(range(20822, 20825)), *list(range(20904, 20933)), *list(range(20934, 20937)), *list(range(21004, 21033)), *list(range(21035, 21038)), *list(range(21095, 21098)), *list(range(21148, 21151)), *list(range(21207, 21265)), 21291, 21292, *list(range(21307, 21365)), *list(range(21413, 21424)), *list(range(21453, 21464)), 21500, *list(range(21780, 21783)), 21818, *list(range(21896, 21900)), 22032, 22033, 22091, 22092, *list(range(22171, 22178)), *list(range(22181, 22188)), *list(range(22191, 22198)), *list(range(22207, 22223)), *list(range(22229, 22233)), 22234, 22235, 22239, 22240, *list(range(22243, 22251)), *list(range(22262, 22266)), 22275, 22277, 22279, 22281, 22283, 22285, 22287, 22289, 22291, 22293, 22300, *list(range(22307, 22323)), 22332, 22337, 22338, *list(range(22348, 22358)), 22391, 22392, *list(range(22407, 22423)), *list(range(22462, 22466)), *list(range(22521, 22526)), *list(range(22607, 22623)), 22639, *list(range(22641, 22647)), *list(range(22648, 22658)), 22700, *list(range(22707, 22723)), 22739, *list(range(22762, 22766)), 22770, 22780, *list(range(22807, 22823)), *list(range(22991, 22995)), *list(range(23028, 23039)), 23090, 23095, 23239, 23240, *list(range(23301, 23334)), 23700, *list(range(23830, 23853)), *list(range(23866, 23873)), *list(range(23877, 23885)), *list(range(23887, 23895)), *list(range(23946, 23949)), 24047, 24048, 24100, 24200, 24305, 24306, *list(range(24311, 24314)), *list(range(24342, 24348)), *list(range(24370, 24384)), 24500, 24547, 24548, 24600, *list(range(24718, 24721)), *list(range(24817, 24822)), *list(range(24877, 24883)), *list(range(24891, 24894)), 25000, 25231, *list(range(25391, 25396)), *list(range(25828, 25838)), 25884, 25932, 26191, 26192, 26194, 26195, 26237, 26331, 26332, *list(range(26391, 26394)), 26632, 26692, *list(range(26701, 26723)), *list(range(26729, 26747)), *list(range(26748, 26761)), *list(range(26766, 26788)), *list(range(26791, 26800)), *list(range(26847, 26871)), *list(range(26891, 26900)), *list(range(26901, 26924)), *list(range(26929, 26947)), *list(range(26948, 26979)), *list(range(26980, 26999)), 27039, 27040, 27120, 27200, *list(range(27205, 27233)), *list(range(27258, 27261)), 27291, 27292, *list(range(27391, 27399)), 27429, 27493, 27500, *list(range(27561, 27565)), *list(range(27571, 27575)), *list(range(27700, 27708)), *list(range(28191, 28194)), 28232, *list(range(28348, 28359)), *list(range(28404, 28433)), 28600, 28991, 28992, 29101, *list(range(29168, 29173)), *list(range(29187, 29196)), 29220, 29221, 29333, 29371, 29373, 29375, 29377, 29379, 29381, 29383, 29385, 29701, 29702, 29738, 29739, 29849, 29850, *list(range(29871, 29875)), *list(range(29901, 29904)), *list(range(30161, 30180)), 30200, 30339, 30340, *list(range(30491, 30495)), *list(range(30729, 30733)), 30791, 30792, 31028, 31121, 31154, 31170, 31171, *list(range(31251, 31260)), *list(range(31281, 31291)), 31300, 31370, *list(range(31466, 31470)), 31528, 31529, 31600, 31838, 31839, 31901, *list(range(31965, 32004)), *list(range(32005, 32018)), *list(range(32019, 32029)), 32030, 32031, *list(range(32033, 32036)), *list(range(32037, 32059)), *list(range(32064, 32068)), *list(range(32081, 32087)), *list(range(32098, 32101)), 32104, *list(range(32107, 32131)), *list(range(32133, 32160)), 32161, *list(range(32164, 32168)), *list(range(32181, 32200)), *list(range(32201, 32261)), *list(range(32301, 32361)), *list(range(32401, 32461)), *list(range(32501, 32561)), *list(range(32600, 32662)), *list(range(32664, 32668)), *list(range(32700, 32762)), 32766],
    'geographic_2d': [3819, 3821, 3824, 3889, 3906, 4023, 4046, 4075, 4081, *list(range(4120, 4125)), *list(range(4127, 4140)), *list(range(4141, 4172)), *list(range(4173, 4177)), *list(range(4178, 4185)), *list(range(4188, 4217)), *list(range(4218, 4226)), 4227, *list(range(4229, 4233)), *list(range(4236, 4260)), *list(range(4261, 4264)), *list(range(4265, 4268)), *list(range(4269, 4280)), *list(range(4281, 4287)), 4288, 4289, 4292, 4293, 4295, *list(range(4297, 4305)), *list(range(4306, 4317)), 4318, 4319, 4322, 4324, 4326, 4463, 4470, 4475, 4483, 4490, 4555, 4558, *list(range(4600, 4631)), 4632, 4633, *list(range(4636, 4640)), *list(range(4641, 4645)), 4646, *list(range(4657, 4681)), *list(range(4682, 4685)), *list(range(4686, 4731)), *list(range(4732, 4766)), *list(range(4801, 4808)), *list(range(4809, 4812)), *list(range(4813, 4819)), 4820, 4821, 4823, 4824, 4901, 4903, 4904, 5013, 5132, 5228, 5229, 5233, 5246, 5252, 5264, 5324, 5340, 5354, 5360, 5365, 5371, 5373, 5381, 5393, 5451, 5464, 5467, 5489, 5524, 5527, 5546, 5561, 5593, 5681, 5886, 6135, 6207, 6311, 6318, 6322, 6325, 6365, 6668, 6706, 6783, *list(range(6881, 6884)), 6892, 6894, 6983, 6990, 7035, 7037, 7039, 7041, 7073, 7084, 7086, 7133, 7136, 7139, 7373, 7683, 7686, 7798, 7844, 7881, 7886, 8042, 8043, 8086, 8232, 8237, 8240, 8246, 8249, 8252, 8255, 8351, 8427, 8428, 8431, 8545, 8685, 8694, 8699, 8818, 8860, 8888, 8900, 8902, 8907, 8949, *list(range(8972, 9001)), 9003, 9006, 9009, 9012, 9014, 9017, 9019, *list(range(9053, 9058)), *list(range(9059, 9070)), 9072, 9075, 9140, 9148, 9153, 9248, 9251, 9253, 9294, 9299, 9309, 9333, 9364, 9372, 9380, 9384, 9403, 9453, 9470, 9474, 9475, 9547, 9696, 9702, 9739, 9755, 9758, 9763, 9777, 9779, 9782, 9784, 9866, 9871, 9939, 9964, 9969, 9974, 9990, 10158, 10175, 10178, 10185, 10191, 10196, 10204, 10209, 10214, 10219, 10224, 10229, 10237, 10249, 10252, 10256, 10260, 10265, 10268, 10272, 10277, 10284, 10299, 10305, 10307, 10310, 10312, 10328, 10345, 10346, 10414, 10468, 10475, 10571, 10606, 10623, 10628, 10636, 10639, 10671, 10673, 10690, 10725, 10736, 10739, 10758, 10762, 10781, 10785, 10800, 20033, 20041, 20046],
    'geocentric': [3822, 3887, 4000, 4039, 4073, 4079, 4465, 4468, 4473, 4479, 4481, 4556, 4882, 4884, 4886, 4888, 4890, 4892, 4894, 4896, 4897, 4899, 4906, 4908, *list(range(4910, 4921)), 4922, 4924, 4926, 4928, 4930, 4932, 4934, 4936, 4938, 4940, 4942, 4944, 4946, 4948, 4950, 4952, 4954, 4956, 4958, 4960, 4962, 4964, 4966, 4970, 4974, 4976, 4978, 4980, 4982, 4984, 4986, 4988, 4990, 4992, 4994, 4996, 4998, 5011, 5244, 5250, 5262, 5322, 5332, 5341, 5352, 5358, 5363, 5368, 5369, 5379, 5391, 5487, 5544, 5558, 5591, 5828, 5884, 6133, 6309, 6317, 6320, 6323, 6363, 6666, 6704, 6781, 6934, 6981, 6988, 7071, 7134, 7137, 7371, 7656, 7658, 7660, 7662, 7664, 7677, 7679, 7681, 7684, 7789, 7796, 7815, 7842, 7879, 7884, 7914, 7916, 7918, 7920, 7922, 7924, 7926, 7928, 7930, 8084, 8227, 8230, 8233, 8238, 8242, 8247, 8250, 8253, 8397, 8401, 8425, 8429, 8541, 8543, 8683, 8697, 8816, 8898, 8905, 8915, 8917, 8919, 8921, 8923, 8925, 8927, 8929, 8931, 8933, 8935, 8937, 8939, 8941, 8943, 8945, 8947, 9001, 9004, 9007, 9010, 9015, 9070, 9073, 9138, 9146, 9151, 9266, 9292, 9307, 9331, 9378, 9468, 9545, 9694, 9700, 9753, 9775, 9780, 9892, 9988, 10176, 10282, 10297, 10303, 10308, 10326, 10412, 10473, 10569, 10604, 10634, 10637, 10669, 10688, 10723, 10734, 10737, 10760, 10779, 10783, 10798, 20039, 20044],
}


def EstimateJpegQuality(jpegTables):
    try:
        qtables = jpegTables.split(b'\xff\xdb', 1)[1]
        qtables = qtables[2:struct.unpack('>H', qtables[:2])[0]]
        # Only process the first table
        if not (qtables[0] & 0xF):
            values = struct.unpack(
                '>64' + ('H' if qtables[0] else 'B'), qtables[1:1 + 64 * (2 if qtables[0] else 1)])
            if values[58] < 100:
                return int(100 - values[58] / 2)
            return int(5000.0 / 2.5 / values[15])
    except Exception:
        pass


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
    doubles = ifd['tags'][Tag.GeoDoubleParamsTag.value]['data'] if Tag.GeoDoubleParamsTag.value in ifd['tags'] else []
    asciis = ifd['tags'][Tag.GeoAsciiParamsTag.value]['data'] if Tag.GeoAsciiParamsTag.value in ifd['tags'] else ''
    for idx in range(4, len(keys), 4):
        keyid, tagval, count, offset = keys[idx:idx + 4]
        if keyid not in GeoTiffGeoKey:
            continue
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
                linePrefix, key, value if isinstance(value, str) else
                ' '.join(str(v) for v in value)))
    return result


Tag = TiffConstantSet(TiffTag, {
    254: {'name': 'NewSubfileType', 'altnames': {'SubfileType', 'OSubFileType'}, 'datatype': Datatype.LONG, 'count': 1, 'bitfield': NewSubfileType, 'desc': 'A general indication of the kind of data contained in this subfile', 'default': 0},
    255: {'name': 'OldSubfileType', 'datatype': Datatype.SHORT, 'count': 1, 'enum': OldSubfileType, 'desc': 'A general indication of the kind of data contained in this subfile.  See NewSubfileType'},
    256: {'name': 'ImageWidth', 'datatype': (Datatype.SHORT, Datatype.LONG), 'count': 1, 'desc': 'The number of columns in the image, i.e., the number of pixels per scanline'},
    257: {'name': 'ImageLength', 'altnames': {'ImageHeight'}, 'datatype': (Datatype.SHORT, Datatype.LONG), 'count': 1, 'desc': 'The number of rows (sometimes described as scanlines) in the image'},
    258: {'name': 'BitsPerSample', 'datatype': Datatype.SHORT, 'desc': 'Number of bits per component', 'default': 1},
    259: {'name': 'Compression', 'datatype': Datatype.SHORT, 'count': 1, 'enum': Compression, 'desc': 'Compression scheme used on the image data'},
    262: {'name': 'Photometric', 'datatype': Datatype.SHORT, 'count': 1, 'enum': Photometric, 'desc': 'The color space of the image data'},
    263: {'name': 'Threshholding', 'datatype': Datatype.SHORT, 'count': 1, 'enum': Thresholding, 'desc': 'For black and white TIFF files that represent shades of gray, the technique used to convert from gray to black and white pixels'},
    264: {'name': 'CellWidth', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'The width of the dithering or halftoning matrix used to create a dithered or halftoned bilevel file'},
    265: {'name': 'CellLength', 'altnames': {'CellHeight'}, 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'The length of the dithering or halftoning matrix used to create a dithered or halftoned bilevel file'},
    266: {'name': 'FillOrder', 'datatype': Datatype.SHORT, 'count': 1, 'enum': FillOrder, 'desc': 'The logical order of bits within a byte'},
    269: {'name': 'DocumentName', 'datatype': Datatype.ASCII, 'desc': 'The name of the document from which this image was scanned'},
    270: {'name': 'ImageDescription', 'datatype': Datatype.ASCII, 'desc': 'A string that describes the subject of the image'},
    271: {'name': 'Make', 'datatype': Datatype.ASCII, 'desc': 'The scanner manufacturer'},
    272: {'name': 'Model', 'datatype': Datatype.ASCII, 'desc': 'The scanner model name or number'},
    273: {'name': 'StripOffsets', 'datatype': (Datatype.SHORT, Datatype.LONG, Datatype.LONG8), 'bytecounts': 'StripByteCounts', 'desc': 'The byte offset of each strip with respect to the beginning of the TIFF file'},
    274: {'name': 'Orientation', 'datatype': Datatype.SHORT, 'count': 1, 'enum': Orientation, 'desc': 'The orientation of the image with respect to the rows and columns'},
    277: {'name': 'SamplesPerPixel', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'The number of components per pixel'},
    278: {'name': 'RowsPerStrip', 'datatype': (Datatype.SHORT, Datatype.LONG), 'count': 1, 'desc': 'The number of rows per strip'},
    279: {'name': 'StripByteCounts', 'datatype': (Datatype.SHORT, Datatype.LONG, Datatype.LONG8), 'desc': 'For each strip, the number of bytes in the strip after compression'},
    280: {'name': 'MinSampleValue', 'datatype': Datatype.SHORT, 'desc': 'The minimum component value used'},
    281: {'name': 'MaxSampleValue', 'datatype': Datatype.SHORT, 'desc': 'The maximum component value used'},
    282: {'name': 'XResolution', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'The number of pixels per ResolutionUnit in the ImageWidth direction'},
    283: {'name': 'YResolution', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'The number of pixels per ResolutionUnit in the ImageLength direction'},
    284: {'name': 'PlanarConfig', 'datatype': Datatype.SHORT, 'count': 1, 'enum': PlanarConfig, 'desc': 'How the components of each pixel are stored'},
    285: {'name': 'PageName', 'datatype': Datatype.ASCII, 'desc': 'The name of the page from which this image was scanned'},
    286: {'name': 'Xposition', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'The X offset in ResolutionUnits of the left side of the image, with respect to the left side of the page'},
    287: {'name': 'Yposition', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'The Y offset in ResolutionUnits of the top of the image, with respect to the top of the page'},
    288: {'name': 'FreeOffsets', 'datatype': (Datatype.LONG, Datatype.LONG8), 'bytecounts': 'FreeByteCounts', 'desc': 'For each string of contiguous unused bytes in a TIFF file, the byte offset of the string'},
    289: {'name': 'FreeByteCounts', 'datatype': (Datatype.LONG, Datatype.LONG8), 'desc': 'For each string of contiguous unused bytes in a TIFF file, the number of bytes in the string'},
    290: {'name': 'GrayResponseUnit', 'altnames': {'GreyResponseUnit'}, 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'The precision of the information contained in the GrayResponseCurve.  The denominator is 10^(this value)', 'default': 2},
    291: {'name': 'GrayResponseCurve', 'altnames': {'GreyResponseCurve'}, 'datatype': Datatype.SHORT, 'desc': 'For grayscale data, the optical density of each possible pixel value'},
    292: {'name': 'T4Options', 'altnames': {'Group3Options'}, 'datatype': Datatype.LONG, 'count': 1, 'bitfield': T4Options, 'default': 0},
    293: {'name': 'T6Options', 'altnames': {'Group4Options'}, 'datatype': Datatype.LONG, 'count': 1, 'bitfield': T6Options, 'default': 0},
    296: {'name': 'ResolutionUnit', 'datatype': Datatype.SHORT, 'count': 1, 'enum': ResolutionUnit, 'desc': 'Units for XResolution and YResolution', 'default': ResolutionUnit.Inch},
    297: {'name': 'PageNumber', 'datatype': Datatype.SHORT, 'count': 2, 'desc': '0-based page number of the document and total pages of the document'},
    300: {'name': 'ColorResponseUnit', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'The precision of the information contained in the GrayResponseCurve.  The denominator is 10^(this value)'},
    301: {'name': 'TransferFunction', 'datatype': Datatype.SHORT, 'desc': 'Describes a transfer function for the image in tabular style'},
    305: {'name': 'Software', 'datatype': Datatype.ASCII, 'desc': 'Name and version number of the software package(s) used to create the image'},
    306: {'name': 'DateTime', 'datatype': Datatype.ASCII, 'count': 20, 'desc': 'Date and time of image creation', 'format': '%Y:%m:%d %H:%M:%S'},
    315: {'name': 'Artist', 'datatype': Datatype.ASCII, 'desc': 'Person who created the image'},
    316: {'name': 'HostComputer', 'datatype': Datatype.ASCII, 'desc': 'The computer and/or operating system in use at the time of image creation'},
    317: {'name': 'Predictor', 'datatype': Datatype.SHORT, 'count': 1, 'enum': Predictor, 'desc': 'A predictor to apply before encoding', 'default': Predictor['None']},
    318: {'name': 'WhitePoint', 'datatype': Datatype.RATIONAL, 'count': 2, 'desc': 'The chromaticity of the white point of the image'},
    319: {'name': 'PrimaryChromaticities', 'datatype': Datatype.RATIONAL, 'count': 6, 'desc': 'The chromaticities of the primaries of the image'},
    320: {'name': 'ColorMap', 'datatype': Datatype.SHORT, 'desc': 'This field defines a Red-Green-Blue color map for palette color images'},
    321: {'name': 'HalftoneHints', 'datatype': Datatype.SHORT, 'count': 2},
    322: {'name': 'TileWidth', 'datatype': (Datatype.SHORT, Datatype.LONG), 'desc': 'The tile width in pixels'},
    323: {'name': 'TileLength', 'altnames': {'TileHeight'}, 'datatype': (Datatype.SHORT, Datatype.LONG), 'desc': 'The tile length (height) in pixels'},
    324: {'name': 'TileOffsets', 'datatype': (Datatype.LONG, Datatype.LONG8), 'bytecounts': 'TileByteCounts', 'desc': 'For each tile, the byte offset of that tile'},
    325: {'name': 'TileByteCounts', 'datatype': (Datatype.LONG, Datatype.LONG8), 'desc': 'For each tile, the number of (compressed) bytes in that tile'},
    326: {'name': 'BadFaxLines', 'datatype': (Datatype.SHORT, Datatype.LONG)},
    327: {'name': 'CleanFaxData', 'datatype': Datatype.SHORT, 'count': 1, 'enum': CleanFaxData},
    328: {'name': 'ConsecutiveBadFaxLines', 'datatype': (Datatype.SHORT, Datatype.LONG)},
    330: {'name': 'SubIFD', 'datatype': (Datatype.IFD, Datatype.IFD8), 'desc': 'A list of additional images'},
    332: {'name': 'InkSet', 'datatype': Datatype.SHORT, 'count': 1, 'enum': InkSet},
    333: {'name': 'InkNames', 'datatype': Datatype.ASCII},
    334: {'name': 'NumberOfInks', 'datatype': Datatype.SHORT, 'count': 1},
    336: {'name': 'DotRange', 'datatype': (Datatype.BYTE, Datatype.SHORT)},
    337: {'name': 'TargetPrinter', 'datatype': Datatype.ASCII},
    338: {'name': 'ExtraSamples', 'datatype': Datatype.SHORT, 'count': 1, 'enum': ExtraSamples},
    339: {'name': 'SampleFormat', 'datatype': Datatype.SHORT, 'enum': SampleFormat, 'desc': 'How to interpret each data sample in a pixel', 'default': SampleFormat.UINT},
    340: {'name': 'SMinSampleValue', 'desc': 'The minimum sample value'},
    341: {'name': 'SMaxSampleValue', 'desc': 'The maximum sample value'},
    343: {'name': 'ClipPath', 'datatype': Datatype.BYTE},
    344: {'name': 'XClipPathUnits', 'datatype': Datatype.DWORD},
    345: {'name': 'YClipPathUnits', 'datatype': Datatype.DWORD},
    346: {'name': 'Indexed', 'datatype': Datatype.SHORT, 'enum': Indexed, 'desc': 'Indexed images are images where the pixels do not represent color values, but rather an index', 'default': Indexed.NotIndexed},
    347: {'name': 'JPEGTables', 'datatype': Datatype.UNDEFINED, 'dump': lambda val, *args: ('estimated quality: %d' % EstimateJpegQuality(val) if EstimateJpegQuality(val) else None), 'dumpraw': lambda val, *args, **kwargs: {'estimated_quality': EstimateJpegQuality(val), 'raw': val}},
    351: {'name': 'OpiProxy'},
    400: {'name': 'GlobalParametersIFD', 'datatype': (Datatype.IFD, Datatype.IFD8)},
    401: {'name': 'ProfileType'},
    402: {'name': 'FaxProfile'},
    403: {'name': 'CodingMethods'},
    404: {'name': 'VersionYear'},
    405: {'name': 'ModeNumber'},
    433: {'name': 'Decode'},
    434: {'name': 'ImageBaseColor'},
    435: {'name': 'T82Options'},
    512: {'name': 'JPEGProc', 'datatype': Datatype.SHORT, 'count': 1, 'enum': JPEGProc},
    513: {'name': 'JPEGIFOffset', 'datatype': (Datatype.LONG, Datatype.LONG8), 'count': 1, 'bytecounts': 'JPEGIFByteCount'},
    514: {'name': 'JPEGIFByteCount', 'datatype': (Datatype.LONG, Datatype.LONG8), 'count': 1},
    515: {'name': 'JPEGRestartInterval', 'datatype': Datatype.SHORT, 'count': 1},
    517: {'name': 'JPEGLosslessPredictors', 'datatype': Datatype.SHORT, 'enum': JPEGLosslessPredictors},
    518: {'name': 'JPEGPointTransform', 'datatype': Datatype.SHORT},
    519: {'name': 'JPEGQTables', 'datatype': (Datatype.LONG, Datatype.LONG8), 'bytecounts': 64},
    520: {'name': 'JPEGDCTables', 'datatype': (Datatype.LONG, Datatype.LONG8), 'bytecounts': 16 + 17},
    521: {'name': 'JPEGACTables', 'datatype': (Datatype.LONG, Datatype.LONG8), 'bytecounts': 16 + 256},
    529: {'name': 'YCbCrCoefficients', 'datatype': Datatype.RATIONAL, 'count': 3},
    530: {'name': 'YCbCrSubsampling', 'datatype': Datatype.SHORT, 'count': 2},
    531: {'name': 'YCbCrPositioning', 'datatype': Datatype.SHORT, 'count': 1, 'enum': YCbCrPositioning},
    532: {'name': 'ReferenceBlackWhite', 'datatype': Datatype.RATIONAL, 'count': 6},
    559: {'name': 'StripRowCounts', 'datatype': Datatype.LONG},
    700: {'name': 'XMLPacket'},
    32781: {'name': 'OPIImageID'},
    32932: {'name': 'WangAnnotation', 'altnames': {'TiffAnnotationData'}},
    32953: {'name': 'RefPts'},
    32954: {'name': 'RegionTackPoint'},
    32955: {'name': 'RegionWarpCorners'},
    32956: {'name': 'RegionAffine'},
    32995: {'name': 'Matteing'},
    32996: {'name': 'Datatype'},
    32997: {'name': 'ImageDepth'},
    32998: {'name': 'TileDepth'},
    33300: {'name': 'PIXAR_ImageFullWidth'},
    33301: {'name': 'PIXAR_ImageFullLength', 'altnames': {'PIXAR_ImageFullHeight'}},
    33302: {'name': 'PIXAR_TextureFormat'},
    33303: {'name': 'PIXAR_WrapModes'},
    33304: {'name': 'PIXAR_FovCot'},
    33305: {'name': 'PIXAR_Matrix_WorldToScreen'},
    33306: {'name': 'PIXAR_Matrix_WorldToCamera'},
    33405: {'name': 'WriterSerialNumber'},
    33421: {'name': 'CFARepeatPatternDim'},
    33422: {'name': 'CFAPattern'},
    33423: {'name': 'BatteryLevel'},
    33432: {'name': 'Copyright', 'datatype': Datatype.ASCII},
    33434: {'name': 'EXPOSURETIME', 'desc': 'Exposure time'},
    33437: {'name': 'FNUMBER', 'desc': 'F number'},
    33445: {'name': 'MDFileTag'},
    33446: {'name': 'MDScalePixel'},
    33447: {'name': 'MDColorTable'},
    33448: {'name': 'MDLabName'},
    33449: {'name': 'MDSampleInfo'},
    33450: {'name': 'MDPrepDate'},
    33451: {'name': 'MDPrepTime'},
    33452: {'name': 'MDFileUnits'},
    33550: {'name': 'ModelPixelScaleTag'},
    33723: {'name': 'RichTiffIPTC', 'altnames': {'IPTC_NAA'}, 'desc': 'Alias IPTC/NAA Newspaper Association RichTIFF'},
    33918: {'name': 'INGRPacketDataTag'},
    33919: {'name': 'INGRFlagRegisters'},
    33920: {'name': 'IrasBTransformationMatrix', 'altnames': {'IRASB_TRANSORMATION_MATRIX'}},
    33922: {'name': 'ModelTiepointTag'},
    34016: {'name': 'IT8Site'},
    34017: {'name': 'IT8ColorSequence'},
    34018: {'name': 'IT8Header'},
    34019: {'name': 'IT8RasterPadding'},
    34020: {'name': 'IT8BitsPerRunLength'},
    34021: {'name': 'IT8BitsPerExtendedRunLength'},
    34022: {'name': 'IT8ColorTable'},
    34023: {'name': 'IT8ImageColorIndicator'},
    34024: {'name': 'IT8BkgColorIndicator'},
    34025: {'name': 'IT8ImageColorValue'},
    34026: {'name': 'IT8BkgColorValue'},
    34027: {'name': 'IT8PixelIntensityRange'},
    34028: {'name': 'IT8TransparencyIndicator'},
    34029: {'name': 'IT8ColorCharacterization'},
    34030: {'name': 'IT8HCUsage'},
    34031: {'name': 'IT8TrapIndicator'},
    34032: {'name': 'IT8CMYKEquivalent'},
    34232: {'name': 'FrameCount'},
    34264: {'name': 'ModelTransformationTag'},
    34377: {'name': 'Photoshop'},
    34665: {'name': 'EXIFIFD', 'datatype': (Datatype.IFD, Datatype.IFD8), 'tagset': EXIFTag},
    34675: {'name': 'ICCProfile'},
    34732: {'name': 'ImageLayer'},
    34735: {'name': 'GeoKeyDirectoryTag', 'dump': lambda *args: GeoKeysToDict(*args) and '', 'dumpraw': GeoKeysToDict},
    34736: {'name': 'GeoDoubleParamsTag'},
    34737: {'name': 'GeoAsciiParamsTag'},
    34750: {'name': 'JBIGOptions'},
    34850: {'name': 'EXPOSUREPROGRAM', 'desc': 'Exposure program'},
    34852: {'name': 'SPECTRALSENSITIVITY', 'desc': 'Spectral sensitivity'},
    34853: {'name': 'GPSIFD', 'datatype': (Datatype.IFD, Datatype.IFD8), 'tagset': GPSTag},
    34855: {'name': 'ISOSPEEDRATINGS', 'desc': 'ISO speed rating'},
    34856: {'name': 'OECF', 'desc': 'Optoelectric conversion factor'},
    34857: {'name': 'INTERLACE', 'desc': 'Number of multi-field images'},
    34858: {'name': 'TIMEZONEOFFSET', 'desc': 'Time zone offset relative to UTC'},
    34859: {'name': 'SELFTIMERMODE', 'desc': 'Number of seconds capture was delayed from button press'},
    36867: {'name': 'DATETIMEORIGINAL', 'desc': 'Date and time of original data generation'},
    37122: {'name': 'COMPRESSEDBITSPERPIXEL', 'desc': 'Image compression mode'},
    37377: {'name': 'SHUTTERSPEEDVALUE', 'desc': 'Shutter speed'},
    37378: {'name': 'APERTUREVALUE', 'desc': 'Aperture'},
    37379: {'name': 'BRIGHTNESSVALUE', 'desc': 'Brightness'},
    37380: {'name': 'EXPOSUREBIASVALUE', 'desc': 'Exposure bias'},
    37381: {'name': 'MAXAPERTUREVALUE', 'desc': 'Maximum lens aperture'},
    37382: {'name': 'SUBJECTDISTANCE', 'desc': 'Subject distance'},
    37383: {'name': 'METERINGMODE', 'desc': 'Metering mode'},
    37384: {'name': 'LIGHTSOURCE', 'desc': 'Light source'},
    37385: {'name': 'FLASH', 'desc': 'Flash'},
    37386: {'name': 'FOCALLENGTH', 'desc': 'Lens focal length'},
    37387: {'name': 'FLASHENERGY', 'desc': 'Flash energy, or range if there is uncertainty'},
    37388: {'name': 'SPATIALFREQUENCYRESPONSE', 'desc': 'Spatial frequency response'},
    37389: {'name': 'NOISE', 'desc': 'Camera noise measurement values'},
    37390: {'name': 'FOCALPLANEXRESOLUTION', 'desc': 'Focal plane X resolution'},
    37391: {'name': 'FOCALPLANEYRESOLUTION', 'desc': 'Focal plane Y resolution'},
    37392: {'name': 'FOCALPLANERESOLUTIONUNIT', 'desc': 'Focal plane resolution unit'},
    37393: {'name': 'IMAGENUMBER', 'desc': 'Number of image when several of burst shot stored in same TIFF/EP'},
    37394: {'name': 'SECURITYCLASSIFICATION', 'desc': 'Security classification'},
    37395: {'name': 'IMAGEHISTORY', 'desc': 'Record of what has been done to the image'},
    37396: {'name': 'SUBJECTLOCATION', 'desc': 'Subject location (area)'},
    37397: {'name': 'EXPOSUREINDEX', 'desc': 'Exposure index'},
    37398: {'name': 'STANDARDID', 'desc': 'TIFF/EP standard version, n.n.n.n'},
    37399: {'name': 'SENSINGMETHOD', 'desc': 'Type of image sensor'},
    34908: {'name': 'FaxRecvParams'},
    34909: {'name': 'FaxSubaddress'},
    34910: {'name': 'FaxRecvTime'},
    34911: {'name': 'FAXDCS'},
    34929: {'name': 'FEDEX_EDR'},
    37439: {'name': 'StoNits'},
    37724: {'name': 'ImageSourceData'},
    40965: {'name': 'InteroperabilityIFD', 'datatype': (Datatype.IFD, Datatype.IFD8), 'tagset': InteroperabilityTag},
    42112: {'name': 'GDAL_Metadata'},
    42113: {'name': 'GDAL_NoData'},
    50215: {'name': 'OceScanjobDescription'},
    50216: {'name': 'OceApplicationSelector'},
    50217: {'name': 'OceIdentificationNumber'},
    50218: {'name': 'OceImageLogicCharacteristics'},
    50674: {'name': 'LERC_PARAMETERS'},
    50706: {'name': 'DNGVersion'},
    50707: {'name': 'DNGBackwardVersion'},
    50708: {'name': 'UniqueCameraModel'},
    50709: {'name': 'LocalizedCameraModel'},
    50710: {'name': 'CFAPlaneColor'},
    50711: {'name': 'CFALayout'},
    50712: {'name': 'LinearizationTable'},
    50713: {'name': 'BlackLevelRepeatDim'},
    50714: {'name': 'BlackLevel'},
    50715: {'name': 'BlackLevelDeltaH'},
    50716: {'name': 'BlackLevelDeltaV'},
    50717: {'name': 'WhiteLevel'},
    50718: {'name': 'DefaultScale'},
    50719: {'name': 'DefaultCropOrigin'},
    50720: {'name': 'DefaultCropSize'},
    50721: {'name': 'ColorMatrix1'},
    50722: {'name': 'ColorMatrix2'},
    50723: {'name': 'CameraCalibration1'},
    50724: {'name': 'CameraCalibration2'},
    50725: {'name': 'ReductionMatrix1'},
    50726: {'name': 'ReductionMatrix2'},
    50727: {'name': 'AnalogBalance'},
    50728: {'name': 'AsShotNeutral'},
    50729: {'name': 'AsShotWhiteXY'},
    50730: {'name': 'BaselineExposure'},
    50731: {'name': 'BaselineNoise'},
    50732: {'name': 'BaselineSharpness'},
    50733: {'name': 'BayerGreenSplit'},
    50734: {'name': 'LinearResponseLimit'},
    50735: {'name': 'CameraSerialNumber'},
    50736: {'name': 'LensInfo'},
    50737: {'name': 'ChromaBlurRadius'},
    50738: {'name': 'AntiAliasStrength'},
    50739: {'name': 'ShadowScale'},
    50740: {'name': 'DNGPrivateData'},
    50741: {'name': 'MakerNoteSafety'},
    50778: {'name': 'CalibrationIlluminant1'},
    50779: {'name': 'CalibrationIlluminant2'},
    50780: {'name': 'BestQualityScale'},
    50784: {'name': 'AliasLayerMetadata'},
    50781: {'name': 'RAWDATAUNIQUEID'},
    50827: {'name': 'ORIGINALRAWFILENAME'},
    50828: {'name': 'ORIGINALRAWFILEDATA'},
    50829: {'name': 'ACTIVEAREA'},
    50830: {'name': 'MASKEDAREAS'},
    50831: {'name': 'ASSHOTICCPROFILE'},
    50832: {'name': 'ASSHOTPREPROFILEMATRIX'},
    50833: {'name': 'CURRENTICCPROFILE'},
    50834: {'name': 'CURRENTPREPROFILEMATRIX'},
    50838: {'name': 'ImageJMetadataByteCounts', 'altnames': {'IJMetadataByteCounts'}, 'datatype': (Datatype.SHORT, Datatype.LONG, Datatype.LONG8)},
    50839: {'name': 'ImageJMetadata', 'altnames': {'ImageJMetadata'}, 'datatype': Datatype.BYTE},
    50844: {'name': 'RPCCOEFFICIENT'},
    50879: {'name': 'COLORIMETRICREFERENCE', 'desc': 'colorimetric reference'},
    50908: {'name': 'TIFF_RSID'},
    50909: {'name': 'GEO_METADATA'},
    50931: {'name': 'CAMERACALIBRATIONSIGNATURE', 'desc': 'camera calibration signature'},
    50932: {'name': 'PROFILECALIBRATIONSIGNATURE', 'desc': 'profile calibration signature'},
    50933: {'name': 'TIFFTAG_EXTRACAMERAPROFILES', 'altnames': {'EXTRACAMERAPROFILES'}},
    50934: {'name': 'ASSHOTPROFILENAME', 'desc': 'as shot profile name'},
    50935: {'name': 'NOISEREDUCTIONAPPLIED', 'desc': 'amount of applied noise reduction'},
    50936: {'name': 'PROFILENAME', 'desc': 'camera profile name'},
    50937: {'name': 'PROFILEHUESATMAPDIMS', 'desc': 'dimensions of HSV mapping'},
    50938: {'name': 'PROFILEHUESATMAPDATA1', 'desc': 'first HSV mapping table'},
    50939: {'name': 'PROFILEHUESATMAPDATA2', 'desc': 'second HSV mapping table'},
    50940: {'name': 'PROFILETONECURVE', 'desc': 'default tone curve'},
    50941: {'name': 'PROFILEEMBEDPOLICY', 'desc': 'profile embedding policy'},
    50942: {'name': 'PROFILECOPYRIGHT', 'desc': 'profile copyright information (UTF-8)'},
    50964: {'name': 'FORWARDMATRIX1', 'desc': 'matrix for mapping white balanced camera colors to XYZ D50'},
    50965: {'name': 'FORWARDMATRIX2', 'desc': 'matrix for mapping white balanced camera colors to XYZ D50'},
    50966: {'name': 'PREVIEWAPPLICATIONNAME', 'desc': 'name of application that created preview (UTF-8)'},
    50967: {'name': 'PREVIEWAPPLICATIONVERSION', 'desc': 'version of application that created preview (UTF-8)'},
    50968: {'name': 'PREVIEWSETTINGSNAME', 'desc': 'name of conversion settings (UTF-8)'},
    50969: {'name': 'PREVIEWSETTINGSDIGEST', 'desc': 'unique id of conversion settings'},
    50970: {'name': 'PREVIEWCOLORSPACE', 'desc': 'preview color space'},
    50971: {'name': 'PREVIEWDATETIME', 'desc': 'date/time preview was rendered'},
    50972: {'name': 'RAWIMAGEDIGEST', 'desc': 'md5 of raw image data'},
    50973: {'name': 'ORIGINALRAWFILEDIGEST', 'desc': 'md5 of the data stored in the OriginalRawFileData tag'},
    50974: {'name': 'SUBTILEBLOCKSIZE', 'desc': 'subtile block size'},
    50975: {'name': 'ROWINTERLEAVEFACTOR', 'desc': 'number of interleaved fields'},
    50981: {'name': 'PROFILELOOKTABLEDIMS', 'desc': 'num of input samples in each dim of default "look" table'},
    50982: {'name': 'PROFILELOOKTABLEDATA', 'desc': 'default "look" table for use as starting point'},
    51008: {'name': 'OPCODELIST1', 'desc': 'opcodes that should be applied to raw image after reading'},
    51009: {'name': 'OPCODELIST2', 'desc': 'opcodes that should be applied after mapping to linear reference'},
    51022: {'name': 'OPCODELIST3', 'desc': 'opcodes that should be applied after demosaicing'},
    51041: {'name': 'NOISEPROFILE', 'desc': 'noise profile'},
    51089: {'name': 'ORIGINALDEFAULTFINALSIZE', 'desc': 'default final size of larger original file for this proxy'},
    51090: {'name': 'ORIGINALBESTQUALITYFINALSIZE', 'desc': 'best quality final size of larger original file for this proxy'},
    51091: {'name': 'ORIGINALDEFAULTCROPSIZE', 'desc': 'the default crop size of larger original file for this proxy'},
    51107: {'name': 'PROFILEHUESATMAPENCODING', 'desc': '3D HueSatMap indexing conversion'},
    51108: {'name': 'PROFILELOOKTABLEENCODING', 'desc': '3D LookTable indexing conversion'},
    51109: {'name': 'BASELINEEXPOSUREOFFSET', 'desc': 'baseline exposure offset'},
    51110: {'name': 'DEFAULTBLACKRENDER', 'desc': 'black rendering hint'},
    51111: {'name': 'NEWRAWIMAGEDIGEST', 'desc': 'modified MD5 digest of the raw image data'},
    51112: {'name': 'RAWTOPREVIEWGAIN', 'desc': 'The gain between the main raw FD and the preview IFD containing this tag'},
    51125: {'name': 'DEFAULTUSERCROP', 'desc': 'default user crop rectangle in relative coords'},
    51177: {'name': 'DEPTHFORMAT', 'desc': 'encoding of the depth data in the file'},
    51178: {'name': 'DEPTHNEAR', 'desc': 'distance from the camera represented by value 0 in the depth map'},
    51179: {'name': 'DEPTHFAR', 'desc': 'distance from the camera represented by the maximum value in the depth map'},
    51180: {'name': 'DEPTHUNITS', 'desc': 'measurement units for DepthNear and DepthFar'},
    51181: {'name': 'DEPTHMEASURETYPE', 'desc': 'measurement geometry for the depth map'},
    51182: {'name': 'ENHANCEPARAMS', 'desc': 'a string that documents how the enhanced image data was processed.'},
    52525: {'name': 'PROFILEGAINTABLEMAP', 'desc': 'spatially varying gain tables that can be applied as starting point'},
    52526: {'name': 'SEMANTICNAME', 'desc': 'a string that identifies the semantic mask'},
    52528: {'name': 'SEMANTICINSTANCEID', 'desc': 'a string that identifies a specific instance in a semantic mask'},
    52529: {'name': 'CALIBRATIONILLUMINANT3', 'desc': 'the illuminant used for the third set of color calibration tags'},
    52530: {'name': 'CAMERACALIBRATION3', 'desc': 'matrix to transform reference camera native space values to individual camera native space values under CalibrationIlluminant3'},
    52531: {'name': 'COLORMATRIX3', 'desc': 'matrix to convert XYZ values to reference camera native color space under CalibrationIlluminant3'},
    52532: {'name': 'FORWARDMATRIX3', 'desc': 'matrix to map white balanced camera colors to XYZ D50'},
    52533: {'name': 'ILLUMINANTDATA1', 'desc': 'data for the first calibration illuminant'},
    52534: {'name': 'ILLUMINANTDATA2', 'desc': 'data for the second calibration illuminant'},
    52536: {'name': 'MASKSUBAREA', 'desc': "the crop rectangle of this IFD's mask, relative to the main image"},
    52537: {'name': 'PROFILEHUESATMAPDATA3', 'desc': 'the data for the third HSV table'},
    52538: {'name': 'REDUCTIONMATRIX3', 'desc': 'dimensionality reduction matrix for use in color conversion to XYZ under CalibrationIlluminant3'},
    52543: {'name': 'RGBTABLES', 'desc': 'color transforms to apply to masked image regions'},
    53535: {'name': 'ILLUMINANTDATA3', 'desc': 'data for the third calibration illuminant'},
    # Aperio tags found in sample files but may not be official
    # 55000 appears to be the position of the scan; top in microns, left in
    # microns, then two other values that are similar to the height and width
    # in microns, but not exact enough to be certain what these mean.
    55000: {'name': 'AperioUnknown55000', 'source': 'sample svs', 'datatype': Datatype.SLONG},
    55001: {'name': 'AperioMagnification', 'source': 'sample svs'},
    55002: {'name': 'AperioMPP', 'source': 'sample svs', 'datatype': Datatype.DOUBLE},
    55003: {'name': 'AperioScanScopeID', 'source': 'sample svs'},
    55004: {'name': 'AperioDate', 'source': 'sample svs'},
    # Hamamatsu tags
    65324: {'name': 'NDPI_OffsetHighBytes', 'source': 'tifffile.py', 'ndpi_offset': True},
    65325: {'name': 'NDPI_ByteCountHighBytes', 'source': 'tifffile.py', 'ndpi_offset': True},
    65420: {'name': 'NDPI_FORMAT_FLAG', 'source': 'hamamatsu'},
    65421: {'name': 'NDPI_SOURCELENS', 'altnames': {'NDPI_Magnification'}, 'source': 'hamamatsu'},
    65422: {'name': 'NDPI_XOFFSET', 'source': 'hamamatsu'},
    65423: {'name': 'NDPI_YOFFSET', 'source': 'hamamatsu'},
    65424: {'name': 'NDPI_FOCAL_PLANE', 'altnames': {'NDPI_ZOFFSET'}, 'source': 'hamamatsu'},
    65425: {'name': 'NDPI_TissueIndex', 'source': 'tifffile.py'},
    65426: {'name': 'NDPI_MCU_STARTS', 'source': 'hamamatsu', 'ndpi_offset': True},
    65427: {'name': 'NDPI_REFERENCE', 'altnames': {'NDPI_SlideLabel'}, 'source': 'hamamatsu'},
    65428: {'name': 'NDPI_AuthCode', 'source': 'tifffile.py'},
    65432: {'name': 'NDPI_McuStartsHighBytes', 'source': 'tifffile.py', 'ndpi_offset': True},
    65434: {'name': 'NDPI_CHANNEL', 'altnames': {'NDPI_Fluorescence'}, 'source': 'hamamatsu'},
    65435: {'name': 'NDPI_ExposureRatio', 'source': 'tifffile.py'},
    65436: {'name': 'NDPI_RedMultiplier', 'source': 'tifffile.py'},
    65437: {'name': 'NDPI_GreenMultiplier', 'source': 'tifffile.py'},
    65438: {'name': 'NDPI_BlueMultiplier', 'source': 'tifffile.py'},
    65439: {'name': 'NDPI_FocusPoints', 'source': 'tifffile.py'},
    65440: {'name': 'NDPI_FocusPointRegions', 'source': 'tifffile.py'},
    65441: {'name': 'NDPI_CaptureMode', 'source': 'tifffile.py'},
    # NDPI_NDPSN is not the official name
    65442: {'name': 'NDPI_NDPSN', 'altnames': {'NDPI_ScannerSerialNumber'}, 'source': 'hamamatsu'},
    65444: {'name': 'NDPI_JpegQuality', 'source': 'tifffile.py'},
    65445: {'name': 'NDPI_RefocusInterval', 'source': 'tifffile.py'},
    65446: {'name': 'NDPI_FocusOffset', 'source': 'tifffile.py'},
    65447: {'name': 'NDPI_BlankLines', 'source': 'tifffile.py'},
    65448: {'name': 'NDPI_FirmwareVersion', 'source': 'tifffile.py'},
    65449: {'name': 'NDPI_PROPERTY_MAP', 'source': 'hamamatsu'},
    65450: {'name': 'NDPI_LabelObscured', 'source': 'tifffile.py'},
    65451: {'name': 'NDPI_EMISSION_WAVELENGTH', 'source': 'hamamatsu'},
    65453: {'name': 'NDPI_LampAge', 'source': 'tifffile.py'},
    65454: {'name': 'NDPI_ExposureTime', 'source': 'tifffile.py'},
    65455: {'name': 'NDPI_FocusTime', 'source': 'tifffile.py'},
    65456: {'name': 'NDPI_ScanTime', 'source': 'tifffile.py'},
    65457: {'name': 'NDPI_WriteTime', 'source': 'tifffile.py'},
    65458: {'name': 'NDPI_FullyAutoFocus', 'source': 'tifffile.py'},
    65500: {'name': 'NDPI_DefaultGamma', 'source': 'tifffile.py'},
    # End Hamamatsu tags
    65535: {'name': 'DCSHUESHIFTVALUES'},
})

Tag.SubIFD.tagset = Tag
Tag.GlobalParametersIFD.tagset = Tag
