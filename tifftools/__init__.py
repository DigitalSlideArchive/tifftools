import argparse
import copy
import logging
import math
import os
import sys

from .constants import Datatype, Tag, TiffDatatype, TiffTag
from .tifftools import read_tiff, write_tiff

logger = logging.getLogger(__name__)


def tiff_merge(*args, **kwargs):
    """
    Alias for tiff_concat.
    """
    return tiff_merge(*args, **kwargs)


def tiff_concat(output, source, overwrite=False, **kwargs):
    """
    Concatenate a list of soruce files into a single output file.

    :param output: the output path
    :param source: a list of input paths
    :overwrite: if False, throw an error if the output already exists.
    """
    ifds = []
    for path in source:
        nextInfo = read_tiff(path)
        ifds.extend(nextInfo['ifds'])
    write_tiff(ifds, output, allowExisting=overwrite)


def _tiff_dump_tag(tag, taginfo, linePrefix, max):
    datatype = Datatype[taginfo['type']]
    sys.stdout.write('%s  %s %s:' % (linePrefix, tag, datatype.name))
    if datatype.pack:
        count = len(taginfo['data']) // len(datatype.pack)
        if count != 1:
            sys.stdout.write(' <%d>' % count)
        for val in taginfo['data'][:max * len(datatype.pack)]:
            sys.stdout.write(
                (' %d' if datatype not in (Datatype.FLOAT, Datatype.DOUBLE) else ' %g') % val)
        if len(taginfo['data']) > max * len(datatype.pack):
            sys.stdout.write(' ...')
    elif datatype == Datatype.ASCII:
        sys.stdout.write(' %s' % taginfo['data'])
    else:
        sys.stdout.write(' <%d> %r' % (len(taginfo['data']), taginfo['data'][:max]))
    sys.stdout.write('\n')


def _tiff_dump_ifds(ifds, max, titlePrefix='', linePrefix='', tagSet=Tag):
    for idx, ifd in enumerate(ifds):
        sys.stdout.write('%s%sDirectory %d: offset %d (0x%x)\n' % (
            linePrefix, titlePrefix, idx, ifd['offset'], ifd['offset']))
        subifdList = []
        for tag, taginfo in sorted(ifd['tags'].items()):
            try:
                tag = tagSet[tag]
            except Exception:
                tag = TiffTag(int(tag), {'name': str(tag), 'datatype': Datatype[taginfo['type']]})
            if not tag.isIFD() and taginfo['type'] not in (Datatype.IFD, Datatype.IFD8):
                _tiff_dump_tag(tag, taginfo, linePrefix, max)
            else:
                subifdList.append((tag, taginfo))
        for tag, taginfo in subifdList:
            subLinePrefix = linePrefix + '  '
            subTitlePrefix = '%s:' % (tag)
            for subidx, subifds in enumerate(taginfo['ifds']):
                _tiff_dump_ifds(
                    subifds,
                    max,
                    subTitlePrefix + '%d, ' % subidx,
                    subLinePrefix, Tag if tag == Tag.SubIFD else None)


def tiff_info(*args, **kwargs):
    """
    Alias for tiff_dump.
    """
    return tiff_dump(*args, **kwargs)


def tiff_dump(source, max=20, *args, **kwargs):
    """
    Print the tiff information.

    :param source: the source path.
    :param max: the maximum number of items to display for lists.
    """
    info = read_tiff(source)
    sys.stdout.write('Header: 0x%02x%02x <%s-endian> <%sTIFF>\n' % (
        info['header'][0], info['header'][1],
        'big' if info['bigEndian'] else 'little',
        'Big' if info['bigtiff'] else 'Classic'))
    _tiff_dump_ifds(info['ifds'], max)


def _iterate_ifds(ifds, subifds=False):
    """
    Iterate through all ifds in a file.  If there are subifds, optionally
    recurse them.

    :param ifds: An array of ifds.
    :param subifds: If True, recurse SubIFDs.
    :param startIndex: starting index value to return.
    :yields: each ifd in turn
    """
    for ifd in ifds:
        yield ifd
        if subifds and int(Tag.SubIFD) in ifd['tags']:
            for subifd in ifd['tags'][int(Tag.SubIFD)]['ifds']:
                yield from _iterate_ifds(subifd, subifds)


def _makeSplitName(prefix, num, neededChars):
    """
    Construct a split name from a prefix, a number, and the number of
    characters needed to represent the number.

    :param prefix: the prefix or None.
    :param num: the zero-based index.
    :param neededChars: the number of characters to appened before the file
        extension.
    :returns: a file path.
    """
    if prefix is None:
        prefix = './'
    suffix = '.tif'
    for _ in range(neededChars):
        suffix = chr((num % 26) + 97) + suffix
        num //= 26
    return str(prefix) + suffix


def tiff_split(source, prefix=None, subifds=False, overwrite=False, **kwargs):
    """
    Split a tiff file into separated directories.

    :param source: the source path.
    :param prefix: the root location for the result.  This will always append
        at least 3 characters followed by .tif.  These are sequential from a to
        z, and always append enough characters to be unique.
    :param subifds: if True, split all subifds into separate files.  Note that
        only the SubIFD tag is so split out (not, for instance, EXIF IFD).
    :param overwrite: if False, throw an error if any of the ouput paths
        already exist.
    """
    info = read_tiff(source)
    numOutput = len(list(_iterate_ifds(info['ifds'], subifds=subifds)))
    neededChars = max(int(math.ceil(math.log(numOutput) / math.log(26))), 3)
    if not overwrite:
        logger.debug('Verifying output files do not exist')
        for idx in range(numOutput):
            outputPath = _makeSplitName(prefix, idx, neededChars)
            if os.path.exists(outputPath):
                raise Exception('File already exists: %s' % outputPath)
    for idx, ifd in enumerate(_iterate_ifds(info['ifds'], subifds=subifds)):
        outputPath = _makeSplitName(prefix, idx, neededChars)
        if subifds and int(Tag.SubIFD) in ifd['tags']:
            ifd = copy.deepcopy(ifd)
            del ifd['tags'][int(Tag.SubIFD)]
        logger.info('Writing %s', outputPath)
        write_tiff(ifd, outputPath, allowExisting=overwrite)


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    description = 'Tiff tools to handle all tags and IFDs.'
    argumentsForAllParsers = [{
        'args': ('--verbose', '-v'),
        'kwargs': dict(action='count', default=0, help='Increase output')
    }, {
        'args': ('--silent', '-s'),
        'kwargs': dict(action='count', default=0, help='Decrease output')
    }]
    mainParser = argparse.ArgumentParser(description=description)
    secondaryParser = argparse.ArgumentParser(description=description, add_help=False)
    subparsers = mainParser.add_subparsers(
        dest='command',
        title='subcommands',
        help='Subcommands.  See <subcommand> --help for details.')

    parserSplit = subparsers.add_parser(
        'split',
        help='split [--subifds] [--overwrite] source [prefix]',
        description='Split IFDs into separate files.')
    parserSplit.add_argument('source', help='Source file to split.')
    parserSplit.add_argument('prefix', nargs='?', help='Prefix of split files.')
    parserSplit.add_argument(
        '--subifds', action='store_true', help='Split all subifds.  If not '
        'specified, each split file is a single IFD with all of its subifds '
        'included in it.  If specified, each subifd is split to its own file.')
    parserSplit.add_argument(
        '--overwrite', '-y', action='store_true',
        help='Allow overwriting an existing output file.')

    parserConcat = subparsers.add_parser(
        'concat',
        aliases=['merge'],
        help='concat [--overwrite] output source [source ...]',
        description='Concatenate multiple files into a single TIFF.')
    parserConcat.add_argument(
        'output', help='Output file.')
    parserConcat.add_argument(
        'source', nargs='+', help='Source files to concatenate.')
    parserConcat.add_argument(
        '--overwrite', '-y', action='store_true',
        help='Allow overwriting an existing output file.')

    parserInfo = subparsers.add_parser(
        'dump',
        aliases=['info'],
        help='dump [--max MAX] source',
        description='Print contents of a TIFF file.')
    parserInfo.add_argument(
        'source', help='Source file.')
    parserInfo.add_argument(
        '--max', '-m', type=int, help='Maximum items to display.', default=20)

    for parser in (secondaryParser, parserSplit, parserConcat, parserInfo):
        for argument in argumentsForAllParsers:
            parser.add_argument(*argument['args'], **argument['kwargs'])

    # This allows argumentsForAllParsers to be either before or after the
    # command.
    secondary, notInSecondary = secondaryParser.parse_known_args(args)
    args = mainParser.parse_args(notInSecondary)
    for k, v in vars(secondary).items():
        setattr(args, k, v)
    logging.basicConfig(
        stream=sys.stderr, level=max(1, logging.WARNING - 10 * (args.verbose + args.silent)))
    logger.debug('Parsed arguments: %r', args)
    func = globals().get('tiff_' + args.command)
    func(**vars(args))


# See http://docs.python.org/3.3/howto/logging.html#configuring-logging-for-a-library
logging.getLogger('tifftools').addHandler(logging.NullHandler())

__all__ = (
    'Datatype', 'TiffDatatype',
    'Tag', 'TiffTag',

    'read_tiff',
    'write_tiff',

    'tiff_concat',
    'tiff_dump',
    'tiff_info',
    'tiff_merge',
    'tiff_split',

    'main',
)
