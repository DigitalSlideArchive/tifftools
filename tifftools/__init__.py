import logging

from pkg_resources import DistributionNotFound, get_distribution

from .commands import main, tiff_concat, tiff_dump, tiff_info, tiff_merge, tiff_set, tiff_split
from .constants import Datatype, Tag, TiffDatatype, TiffTag
from .exceptions import MustBeBigTiffException, TifftoolsException, UnknownTagException
from .tifftools import read_tiff, write_tiff

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    __version__ = 'development'


logger = logging.getLogger(__name__)

# See http://docs.python.org/3.3/howto/logging.html#configuring-logging-for-a-library
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = (
    'Datatype', 'TiffDatatype',
    'Tag', 'TiffTag',

    'TifftoolsException',
    'UnknownTagException',
    'MustBeBigTiffException',

    'read_tiff',
    'write_tiff',

    'tiff_concat',
    'tiff_dump',
    'tiff_info',
    'tiff_merge',
    'tiff_set',
    'tiff_split',

    '__version__',
    'main',
)
