# flake8: noqa 501
# Disable flake8 line-length check (E501), it makes this file harder to read

import struct

from .exceptions import UnknownTagException


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
        if hasattr(self, str(key)):
            return getattr(self, str(key))
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
        return self.name.lower() == other.lower()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __contains__(self, other):
        return hasattr(self, str(other))

    def __hash__(self):
        return hash((type(self).__name__, self.value))

    def get(self, key, default=None):
        if hasattr(self, str(key)):
            return getattr(self, str(key))
        return default


class TiffTag(TiffConstant):
    def isOffsetData(self):
        return 'bytecounts' in self

    def isIFD(self):
        datatypes = self.get('datatype', None)
        if not isinstance(datatypes, tuple):
            datatypes = (datatypes, )
        for datatype in datatypes:
            if datatype in (Datatype.IFD, Datatype.IFD8):
                return True
        return False


class TiffConstantSet(object):
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
            names[entry.name.lower()] = entry
            names[str(int(entry))] = entry
            if 'altnames' in v:
                for altname in v['altnames']:
                    names[altname.lower()] = entry
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
        if key.lower() in self.__dict__:
            return self.__dict__[key.lower()]
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
        for k, v in sorted(self._entries.items()):
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
        raise UnknownTagException('Unknown tag %s' % key)
    tagClass = tagSet._setClass if tagSet else TiffConstant
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
    6: {'name': 'OldJPEG', 'desc': 'Pre-version 6.0 JPEG', 'lossy': True},
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
    33005: {'name': 'JP2kRGB', 'desc': 'JPEG 2000 with RGB format as used by Aperio', 'lossy': True},
    34661: {'name': 'JBIG', 'desc': 'ISO JBIG'},
    34676: {'name': 'SGILOG', 'desc': 'SGI Log Luminance RLE'},
    34677: {'name': 'SGILOG24', 'desc': 'SGI Log 24-bit packed'},
    34712: {'name': 'JP2000', 'desc': 'Leadtools JPEG2000', 'lossy': True},
    34887: {'name': 'LERC', 'desc': 'ESRI Lerc codec: https://github.com/Esri/lerc', 'lossy': True},
    34925: {'name': 'LZMA', 'desc': 'LZMA2'},
    50000: {'name': 'ZSTD', 'desc': 'ZSTD'},
    50001: {'name': 'WEBP', 'desc': 'WEBP', 'lossy': True},
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
    32845: {'name': 'LogLuv', 'desc': 'CIE Log2(L) (u\',v\')'},
})

Thresholding = TiffConstantSet('TiffThresholding', {
    1: {'name': 'Bilevel', 'desc': 'No dithering or halftoning has been applied to the image data'},
    2: {'name': 'Halftone', 'desc': 'An ordered dither or halftone technique has been applied to the image data'},
    3: {'name': 'ErrorDiffuse', 'desc': 'A randomized process such as error diffusion has been applied to the image data'},
})

FillOrder = TiffConstantSet('TiffFillOrder', {
    1: {'name': 'MSBToLSB', 'desc': 'Pixels are arranged within a byte such that pixels with lower column values are stored in the higher-order bits of the byte'},
    2: {'name': 'LSBToMSB', 'desc': 'Pixels are arranged within a byte such that pixels with lower column values are stored in the lower-order bits of the byte'},
})

Orientation = TiffConstantSet('Orientation', {
    1: {'name': 'TopLeft', 'desc': 'Row 0 top, column 0 left'},
    2: {'name': 'TopRight', 'desc': 'Row 0 top, column 0 right'},
    3: {'name': 'BottomRight', 'desc': 'Row 0 bottom, column 0 right'},
    4: {'name': 'BottomLeft', 'desc': 'Row 0 bottom, column 0 left'},
    5: {'name': 'LeftTop', 'desc': 'Row 0 left, column 0 top'},
    6: {'name': 'RightTop', 'desc': 'Row 0 right, column 0 top'},
    7: {'name': 'RightBottom', 'desc': 'Row 0 right, column 0 bottom'},
    8: {'name': 'LeftBottom', 'desc': 'Row 0 left, column 0 bottom'},
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
    0: {'name': 'All'},
    1: {'name': 'Regenerated'},
    2: {'name': 'Present'},
})

InkSet = TiffConstantSet('InkSet', {
    1: {'name': 'CMYK'},
    2: {'name': 'NotCMYK'},
})

ExtraSamples = TiffConstantSet('ExtraSamples', {
    0: {'name': 'Unspecified'},
    1: {'name': 'AssociatedAlpha'},
    2: {'name': 'UnassociatedAlpha'},
})

SampleFormat = TiffConstantSet('SampleFormat', {
    1: {'name': 'uint', 'altnames': {'UnsignedInteger'}},
    2: {'name': 'int'},
    3: {'name': 'float', 'altnames': {'IEEEFP'}},
    4: {'name': 'Undefined'},
    5: {'name': 'ComplexInt'},
    6: {'name': 'ComplexFloat'},
})

Indexed = TiffConstantSet('Indexed', {
    0: {'name': 'NotIndexed'},
    1: {'name': 'Indexed'},
})

JPEGProc = TiffConstantSet('JPEGProc', {
    1: {'name': 'Baseline'},
    2: {'name': 'LosslessHuffman'},
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
    34855: {'name': 'ISOSpeedRatings', 'datatype': Datatype.SHORT, 'desc': 'ISO speed rating'},
    34856: {'name': 'OECF', 'datatype': Datatype.UNDEFINED, 'desc': 'Optoelectric conversion factor'},
    34858: {'datatype': Datatype.SSHORT, 'name': 'TimeZoneOffset'},
    34859: {'datatype': Datatype.SHORT, 'name': 'SelfTimerMode'},
    36864: {'name': 'ExifVersion', 'datatype': Datatype.UNDEFINED, 'count': 4, 'desc': ' Exif version'},
    34865: {'datatype': Datatype.LONG, 'name': 'StandardOutputSensitivity'},
    34866: {'datatype': Datatype.LONG, 'name': 'RecommendedExposureIndex'},
    36867: {'name': 'DateTimeOriginal', 'datatype': Datatype.ASCII, 'count': 20, 'desc': 'Date and time of original data'},
    36868: {'name': 'DateTimeDigitized', 'datatype': Datatype.ASCII, 'count': 20, 'desc': 'Date and time of digital data'},
    34869: {'datatype': Datatype.LONG, 'name': 'ISOSpeedLatitudezzz'},
    36864: {'name': 'ExifVersion'},
    36867: {'datatype': Datatype.ASCII, 'name': 'DateTimeOriginal'},
    36868: {'datatype': Datatype.ASCII, 'name': 'CreateDate'},
    36873: {'name': 'GooglePlusUploadCode'},
    36880: {'datatype': Datatype.ASCII, 'name': 'OffsetTime'},
    36881: {'datatype': Datatype.ASCII, 'name': 'OffsetTimeOriginal'},
    36882: {'datatype': Datatype.ASCII, 'name': 'OffsetTimeDigitized'},
    37121: {'name': 'ComponentsConfiguration', 'datatype': Datatype.UNDEFINED, 'count': 4, 'desc': ' Meaning of each component'},
    37122: {'name': 'CompressedBitsPerPixel', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': ' Image compression mode'},
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
    37500: {'name': 'MakerNote', 'datatype': Datatype.UNDEFINED, 'desc': ' Manufacturer notes'},
    37510: {'name': 'UserComment', 'datatype': Datatype.UNDEFINED, 'desc': ' User comments'},
    37520: {'name': 'SubSecTime', 'datatype': Datatype.ASCII, 'desc': ' DateTime subseconds'},
    37521: {'name': 'SubSecTimeOriginal', 'datatype': Datatype.ASCII, 'desc': ' DateTimeOriginal subseconds'},
    37522: {'name': 'SubSecTimeDigitized', 'datatype': Datatype.ASCII, 'desc': ' DateTimeDigitized subseconds'},
    37888: {'datatype': Datatype.SRATIONAL, 'name': 'AmbientTemperature'},
    37889: {'datatype': Datatype.RATIONAL, 'name': 'Humidity'},
    37890: {'datatype': Datatype.RATIONAL, 'name': 'Pressure'},
    37891: {'datatype': Datatype.SRATIONAL, 'name': 'WaterDepth'},
    37892: {'datatype': Datatype.RATIONAL, 'name': 'Acceleration'},
    37893: {'datatype': Datatype.SRATIONAL, 'name': 'CameraElevationAngle'},
    40960: {'name': 'FlashpixVersion', 'datatype': Datatype.UNDEFINED, 'count': 4, 'desc': 'Supported Flashpix version'},
    40961: {'name': 'ColorSpace', 'datatype': Datatype.SHORT, 'count': 1, 'desc': ' Color space information'},
    40962: {'name': 'PixelXDimension', 'datatype': (Datatype.SHORT, Datatype.LONG), 'count': 1, 'desc': 'Valid image width'},
    40963: {'name': 'PixelYDimension', 'datatype': (Datatype.SHORT, Datatype.LONG), 'count': 1, 'desc': 'Valid image height'},
    40964: {'name': 'RelatedSoundFile', 'datatype': Datatype.ASCII, 'count': 13, 'desc': ' Related audio file'},
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
    42016: {'name': 'ImageUniqueID', 'datatype': Datatype.ASCII, 'count': 33, 'desc': ' Unique image ID'},
    42032: {'datatype': Datatype.ASCII, 'name': 'OwnerName'},
    42033: {'datatype': Datatype.ASCII, 'name': 'SerialNumber'},
    42034: {'datatype': Datatype.RATIONAL, 'name': 'LensInfo'},
    42035: {'datatype': Datatype.ASCII, 'name': 'LensMake'},
    42036: {'datatype': Datatype.ASCII, 'name': 'LensModel'},
    42037: {'datatype': Datatype.ASCII, 'name': 'LensSerialNumber'},
    42080: {'datatype': Datatype.SHORT, 'name': 'CompositeImage'},
    42081: {'datatype': Datatype.SHORT, 'name': 'CompositeImageCount'},
    42082: {'name': 'CompositeImageExposureTimes'},
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
    0: {'name': 'GPSVersionID', 'datatype': Datatype.BYTE, 'count': 4, 'desc': 'GPS tag version'},
    1: {'name': 'GPSLatitudeRef', 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'North or South Latitude'},
    2: {'name': 'GPSLatitude', 'datatype': Datatype.RATIONAL, 'count': 3, 'desc': 'Latitude'},
    3: {'name': 'GPSLongitudeRef', 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'East or West Longitude'},
    4: {'name': 'GPSLongitude', 'datatype': Datatype.RATIONAL, 'count': 3, 'desc': 'Longitude'},
    5: {'name': 'GPSAltitudeRef', 'datatype': Datatype.BYTE, 'count': 1, 'desc': 'Altitude reference'},
    6: {'name': 'GPSAltitude', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Altitude'},
    7: {'name': 'GPSTimeStamp', 'datatype': Datatype.RATIONAL, 'count': 3, 'desc': 'GPS time (atomic clock)'},
    8: {'name': 'GPSSatellites', 'datatype': Datatype.ASCII, 'desc': 'GPS satellites used for measurement'},
    9: {'name': 'GPSStatus', 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'GPS receiver status'},
    10: {'name': 'GPSMeasureMode', 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'GPS measurement mode'},
    11: {'name': 'GPSDOP', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Measurement precision'},
    12: {'name': 'GPSSpeedRef', 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'Speed unit'},
    13: {'name': 'GPSSpeed', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Speed of GPS receiver'},
    14: {'name': 'GPSTrackRef', 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'Reference for direction of movement'},
    15: {'name': 'GPSTrack', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Direction of movement'},
    16: {'name': 'GPSImgDirectionRef', 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'Reference for direction of image'},
    17: {'name': 'GPSImgDirection', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Direction of image'},
    18: {'name': 'GPSMapDatum', 'datatype': Datatype.ASCII, 'desc': 'Geodetic survey data used'},
    19: {'name': 'GPSDestLatitudeRef', 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'Reference for latitude of destination'},
    20: {'name': 'GPSDestLatitude', 'datatype': Datatype.RATIONAL, 'count': 3, 'desc': 'Latitude of destination'},
    21: {'name': 'GPSDestLongitudeRef', 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'Reference for longitude of destination'},
    22: {'name': 'GPSDestLongitude', 'datatype': Datatype.RATIONAL, 'count': 3, 'desc': 'Longitude of destination'},
    23: {'name': 'GPSDestBearingRef', 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'Reference for bearing of destination'},
    24: {'name': 'GPSDestBearing', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Bearing of destination'},
    25: {'name': 'GPSDestDistanceRef', 'datatype': Datatype.ASCII, 'count': 2, 'desc': 'Reference for distance to destination'},
    26: {'name': 'GPSDestDistance', 'datatype': Datatype.RATIONAL, 'count': 1, 'desc': 'Distance to destination'},
    27: {'name': 'GPSProcessingMethod', 'datatype': Datatype.UNDEFINED, 'desc': 'Name of GPS processing method'},
    28: {'name': 'GPSAreaInformation', 'datatype': Datatype.UNDEFINED, 'desc': 'Name of GPS area'},
    29: {'name': 'GPSDateStamp', 'datatype': Datatype.ASCII, 'count': 11, 'desc': 'GPS date'},
    30: {'name': 'GPSDifferential', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'GPS differential correction'},
})

InteroperabilityTag = TiffConstantSet(TiffTag, {
    1: {'name': 'InteroperabilityIndex', 'datatype': Datatype.ASCII},
})

def EstimateJpegQuality(jpegTables):
    try:
        qtables = jpegTables.split(b'\xff\xdb', 1)[1]
        qtables = qtables[2:struct.unpack('>H', qtables[:2])[0]]
        # Only process the first table
        if not (qtables[0] & 0xF):
            values = struct.unpack('>64' + ('H' if qtables[0] else 'B'), qtables[1:1 + 64 * (2 if qtables[0] else 1)])
            if values[58] < 100:
                return int(100 - values[58] / 2)
            return int(5000.0 / 2.5 / values[15])
    except Exception:
        pass

Tag = TiffConstantSet(TiffTag, {
    254: {'name': 'NewSubfileType', 'altnames': {'SubfileType'}, 'datatype': Datatype.LONG, 'count': 1, 'bitfield': NewSubfileType, 'desc': 'A general indication of the kind of data contained in this subfile', 'default': 0},
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
    300: {'name': 'ColorResponseUunit', 'datatype': Datatype.SHORT, 'count': 1, 'desc': 'The precision of the information contained in the GrayResponseCurve.  The denominator is 10^(this value)'},
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
    347: {'name': 'JPEGTables', 'datatype': Datatype.UNDEFINED, 'dump': lambda val: ('estimated quality: %d' % EstimateJpegQuality(val) if EstimateJpegQuality(val) else None)},
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
    32932: {'name': 'WangAnnotation'},
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
    33432: {'name': 'Copyright', 'datatype': Datatype.ASCII},
    33445: {'name': 'MDFileTag'},
    33446: {'name': 'MDScalePixel'},
    33447: {'name': 'MDColorTable'},
    33448: {'name': 'MDLabName'},
    33449: {'name': 'MDSampleInfo'},
    33450: {'name': 'MDPrepDate'},
    33451: {'name': 'MDPrepTime'},
    33452: {'name': 'MDFileUnits'},
    33550: {'name': 'ModelPixelScaleTag'},
    33723: {'name': 'RichTiffIPTC'},
    33918: {'name': 'INGRPacketDataTag'},
    33919: {'name': 'INGRFlagRegisters'},
    33920: {'name': 'IrasBTransformationMatrix'},
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
    34735: {'name': 'GeoKeyDirectoryTag'},
    34736: {'name': 'GeoDoubleParamsTag'},
    34737: {'name': 'GeoAsciiParamsTag'},
    34750: {'name': 'JBIGOptions'},
    34853: {'name': 'GPSIFD', 'datatype': (Datatype.IFD, Datatype.IFD8), 'tagset': GPSTag},
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
    50908: {'name': 'TIFF_RSID'},
    50909: {'name': 'GEO_METADATA'},
    # Hamamatsu tags
    65420: {'name': 'NDPI_FORMAT_FLAG', 'source': 'hamamatsu'},
    65421: {'name': 'NDPI_SOURCELENS', 'source': 'hamamatsu'},
    65422: {'name': 'NDPI_XOFFSET', 'source': 'hamamatsu'},
    65423: {'name': 'NDPI_YOFFSET', 'source': 'hamamatsu'},
    65424: {'name': 'NDPI_FOCAL_PLANE', 'source': 'hamamatsu'},
    65426: {'name': 'NDPI_MCU_STARTS', 'source': 'hamamatsu'},
    65427: {'name': 'NDPI_REFERENCE', 'source': 'hamamatsu'},
    65442: {'name': 'NDPI_NDPSN', 'source': 'hamamatsu'},  # not offical name
    65449: {'name': 'NDPI_PROPERTY_MAP', 'source': 'hamamatsu'},
    # End Hamamatsu tags
    65535: {'name': 'DCSHUESHIFTVALUES'},
})

Tag.SubIFD.tagset = Tag
Tag.GlobalParametersIFD.tagset = Tag
