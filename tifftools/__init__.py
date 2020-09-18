import logging

from .commands import main, tiff_concat, tiff_dump, tiff_info, tiff_merge, tiff_set, tiff_split
from .constants import Datatype, Tag, TiffDatatype, TiffTag
from .tifftools import read_tiff, write_tiff

logger = logging.getLogger(__name__)

# See http://docs.python.org/3.3/howto/logging.html#configuring-logging-for-a-library
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = (
    'Datatype', 'TiffDatatype',
    'Tag', 'TiffTag',

    'read_tiff',
    'write_tiff',

    'tiff_concat',
    'tiff_dump',
    'tiff_info',
    'tiff_merge',
    'tiff_set',
    'tiff_split',

    'main',
)
