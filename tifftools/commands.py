import argparse
import copy
import json
import logging
import math
import os
import re
import shutil
import struct
import sys
import tempfile

from .constants import Datatype, Tag, get_or_create_tag
from .exceptions import TifftoolsException
from .tifftools import read_tiff, read_tiff_limit_ifds, write_tiff

logger = logging.getLogger(__name__)


class ThrowOnLevelHandler(logging.NullHandler):
    def handle(self, record):
        raise TifftoolsException(record.getMessage())


def _apply_flags_to_ifd(ifd, bigtiff=None, bigendian=None, **kwargs):
    """
    Change the ifd to specify bigtiff and endian options.

    :param ifd: an ifd record to modify or a list of ifds where the first
        entry is modified.
    :param bigtiff: if True, make result bigtiff.  If False, make result
        classic tiff if small enough.  If None, don't change.
    :param bigendian: if True, make result big-endian.  If False, make result
        little-endian.  If None, don't change.
    """
    if not isinstance(ifd, dict):
        ifd = ifd[0]
    if bigtiff is not None:
        ifd['bigtiff'] = bool(bigtiff)
    if bigendian is not None:
        ifd['bigEndian'] = bool(bigendian)


def tiff_merge(*args, **kwargs):
    """
    Alias for tiff_concat.
    """
    return tiff_concat(*args, **kwargs)


def tiff_concat(source, output, overwrite=False, **kwargs):
    """
    Concatenate a list of soruce files into a single output file.

    :param source: a list of input paths
    :param output: the output path
    :overwrite: if False, throw an error if the output already exists.
    """
    ifds = []
    for path in source:
        nextInfo = read_tiff(path)
        ifds.extend(nextInfo['ifds'])
    _apply_flags_to_ifd(ifds, **kwargs)
    write_tiff(ifds, output, allowExisting=overwrite)


def _tiff_dump_tag(tag, taginfo, linePrefix, max, dest=None):
    """
    Print a tag to a string.

    :param tag: the TiffTag class of the tag that should be printed.
    :param taginfo: a dictionary with 'data' and 'datatype' with tag information.
    :param linePrefix: a string to put in front of the output.  This is usually
        whitespace.
    :param dest: the stream to print results to.
    """
    dest = sys.stdout if dest is None else dest
    datatype = Datatype[taginfo['datatype']]
    dest.write('%s  %s %s:' % (linePrefix, tag, datatype.name))
    if datatype.pack:
        count = len(taginfo['data']) // len(datatype.pack)
        if count != 1:
            dest.write(' <%d>' % count)
        for validx, val in enumerate(taginfo['data'][:max * len(datatype.pack)]):
            dest.write(
                (' %d' if datatype not in (Datatype.FLOAT, Datatype.DOUBLE) else ' %.10g') % val)
            if datatype in (Datatype.RATIONAL, Datatype.SRATIONAL) and (validx % 2) and val:
                dest.write(' (%.8g)' % (taginfo['data'][validx - 1] / val))
            if 'enum' in tag and val in tag.enum:
                dest.write(' (%s)' % tag.enum[val])
            if 'bitfield' in tag and val:
                first = True
                for bitfield in tag.bitfield:
                    if (val & bitfield.bitfield) == bitfield.value:
                        dest.write('%s%s' % (' (' if first else ', ', bitfield))
                        first = False
                dest.write(')')
        if len(taginfo['data']) > max * len(datatype.pack):
            dest.write(' ...')
    elif datatype == Datatype.ASCII:
        dest.write(' %s' % taginfo['data'])
    else:
        dest.write(' <%d> %r' % (len(taginfo['data']), taginfo['data'][:max]))
        if len(taginfo['data']) > max:
            dest.write(' ...')
    if 'dump' in tag:
        extra = tag.dump(taginfo['data'])
        if extra:
            dest.write(' (%s)' % extra)
    dest.write('\n')


def _tiff_dump_ifds(ifds, max, dest=None, dirPrefix='', linePrefix='', tagSet=Tag):
    """
    Print a list of ifds to a stream.

    :param ifds: the list of ifds.
    :param max: the maximum number of data values to print.
    :param dest: the stream to print results to.
    :param dirPrefix: a string to add in front of each directory.
    :param linePrefix: a string to put in front of each line.  This is usually
        whitespace.
    :param tagSet: the TiffTagSet class of tags to use for these IFDs.
    """
    dest = sys.stdout if dest is None else dest
    for idx, ifd in enumerate(ifds):
        dest.write('%sDirectory %s%d: offset %d (0x%x)\n' % (
            linePrefix, dirPrefix, idx, ifd['offset'], ifd['offset']))
        subifdList = []
        for tag, taginfo in sorted(ifd['tags'].items()):
            tag = get_or_create_tag(tag, tagSet, {'datatype': Datatype[taginfo['datatype']]})
            if not tag.isIFD() and taginfo['datatype'] not in (Datatype.IFD, Datatype.IFD8):
                _tiff_dump_tag(tag, taginfo, linePrefix, max, dest)
            else:
                subifdList.append((tag, taginfo))
        for tag, taginfo in subifdList:
            subLinePrefix = linePrefix + '  '
            subDirPrefix = '%s%d,%s:' % (dirPrefix, idx, tag.name)
            for subidx, subifds in enumerate(taginfo['ifds']):
                dest.write('%s%s:%d\n' % (subLinePrefix, tag, subidx))
                _tiff_dump_ifds(
                    subifds, max, dest, '%s%d,' % (subDirPrefix, subidx),
                    subLinePrefix + '  ', getattr(tag, 'tagset', None))


def tiff_info(*args, **kwargs):
    """
    Alias for tiff_dump.
    """
    return tiff_dump(*args, **kwargs)


class ExtendedJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        return '%s:%s' % (type(obj).__name__, repr(obj))


def tiff_dump(source, max=20, dest=None, *args, **kwargs):
    """
    Print the tiff information.

    :param source: the source path or a list of source paths.
    :param max: the maximum number of items to display for lists.
    :param dest: an open stream to write to.
    """
    dest = sys.stdout if dest is None else dest
    if isinstance(source, list):
        if kwargs.get('json'):
            dest.write('{\n')
        for srcidx, src in enumerate(source):
            if kwargs.get('json'):
                json.dump(src, dest)
                dest.write(': ')
            else:
                dest.write('-- %s --\n' % src)
            tiff_dump(src, max=max, dest=dest, *args, **kwargs)
            if kwargs.get('json'):
                dest.write(',\n' if srcidx + 1 != len(source) else '\n}')
        return
    info = read_tiff(source)
    if kwargs.get('json'):
        json.dump(info, dest, indent=2, cls=ExtendedJsonEncoder)
        return
    dest.write('Header: 0x%02x%02x <%s-endian> <%sTIFF>\n' % (
        info['header'][0], info['header'][1],
        'big' if info['bigEndian'] else 'little',
        'Big' if info['bigtiff'] else 'Classic'))
    _tiff_dump_ifds(info['ifds'], max, dest)


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


def _make_split_name(prefix, num, neededChars):
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
            outputPath = _make_split_name(prefix, idx, neededChars)
            if os.path.exists(outputPath):
                raise TifftoolsException('File already exists: %s' % outputPath)
    for idx, ifd in enumerate(_iterate_ifds(info['ifds'], subifds=subifds)):
        outputPath = _make_split_name(prefix, idx, neededChars)
        if subifds and int(Tag.SubIFD) in ifd['tags']:
            ifd = copy.deepcopy(ifd)
            del ifd['tags'][int(Tag.SubIFD)]
        logger.info('Writing %s', outputPath)
        _apply_flags_to_ifd(ifd, **kwargs)
        write_tiff(ifd, outputPath, allowExisting=overwrite)


def _value_to_types_numeric(results):
    """
    Parse a string value into a numeric array of possible different datatypes.

    :param results: results dictionary with an entry for Datatype.ASCII.
        Modified.
    """
    floatList = []
    intList = []
    for part in results[Datatype.ASCII].replace(',', ' ').strip().split():
        try:
            asFloat = float(part)
        except ValueError:
            asFloat = None
        try:
            asInt = int(part)
        except ValueError:
            try:
                asInt = int(part, 0)
            except ValueError:
                asInt = None
        floatList.append(asFloat if asFloat is not None else asInt)
        intList.append(asInt if asInt is not None else asFloat)
    for datatype in Datatype:
        if datatype.pack is None:
            continue
        data = floatList if datatype in {Datatype.FLOAT, Datatype.DOUBLE} else intList
        if None in data:
            continue
        try:
            struct.pack(datatype.pack * (len(intList) // len(datatype.pack)), *data)
        except (struct.error, ValueError):
            continue
        results[datatype] = data


def _value_to_types(value):
    """
    Given a value, parse it into any datatypes that make sense.

    :param value: the value to parse.  @<filename> to read binary data from a
        file, @- to read binary data from stdin.  This must either be a string
        or bytes.
    :returns: a dictionary of datatypes and the parsed values.
    """
    if value in ('@-', b'@-'):
        value = sys.stdin.buffer.read()
    elif isinstance(value, str) and value.startswith('@'):
        value = open(value[1:], 'rb').read()
    results = {Datatype.UNDEFINED: value if isinstance(value, bytes) else str(value).encode()}
    if isinstance(value, bytes):
        try:
            results[Datatype.ASCII] = value.decode()
        except UnicodeDecodeError:
            pass
    else:
        results[Datatype.ASCII] = str(value)
    if Datatype.ASCII in results and re.search(r'\d', results[Datatype.ASCII]):
        _value_to_types_numeric(results)
    return results


def _tagspec_to_ifd(tagspec, info, value=None):
    """
    Given a tag specification of the form
    <tag name or number>[:<datatype>][,<ifd-#>[,...]] and a value,
    return the tag, datatype, ifd, and parsed value.

    :param tagspec: the tag specification.
    :param info: the tiff file's info as loaded by read_tiff.
    :param value: a value used to determine a datatype.  If None, the datatype
        is solely from the tag specification.  If the value is prefixed with
        @, it is a part of a file.  Depending on the datatype, the value may be
        a comma or white-space separated list of numerical values.
    :returns: tag, a TiffConstant tag value.
    :returns: datatype, either a TiffDatatype or None.
    :returns: ifd: an ifd record for this tag.
    :returns: data: the parsed value.
    """
    data = None
    if value is not None:
        valueTypes = _value_to_types(value)
    ifd, tagSet = info['ifds'][0], Tag
    if ',' in tagspec:
        tagspec, ifdspec = tagspec.split(',', 1)
        limitedInfo, tagSet = read_tiff_limit_ifds(info, ifdspec.split(','))
        ifd = limitedInfo['ifds'][0]
    datatype = None
    if ':' in tagspec:
        tagspec, datatype = tagspec.split(':', 1)
        if datatype not in Datatype:
            raise TifftoolsException('Unknown datatype %s' % datatype)
        datatype = Datatype[datatype]
        if value is not None and datatype not in valueTypes:
            raise TifftoolsException(
                'Value %r cannot be converted to datatype %s' % (value, datatype))
    tag = get_or_create_tag(tagspec, tagSet, **({'datatype': datatype} if datatype else {}))
    if 'datatype' in tag:
        tagDatatypes = tag.datatype if isinstance(tag.datatype, tuple) else (tag.datatype, )
    if datatype is None and 'datatype' in tag:
        datatype = next((dt for dt in tagDatatypes if value is None or dt in valueTypes), None)
    if value is not None:
        if datatype is None:
            datatype = next((dt for dt in (
                Datatype.BYTE, Datatype.SHORT, Datatype.LONG, Datatype.LONG8,
                Datatype.SBYTE, Datatype.SSHORT, Datatype.SLONG, Datatype.SLONG8,
                Datatype.DOUBLE, Datatype.ASCII
            ) if dt in valueTypes), Datatype.UNDEFINED)
        if 'datatype' in tag and datatype not in tagDatatypes:
            logger.warning(
                'Value %r is datatype %s which is not a known datatype for tag %s.',
                data, datatype, tag)
        data = valueTypes.get(datatype)
        if 'enum' in tag and any(v for v in data if v not in tag.enum):
            logger.warning('Value %r is not in known values for tag %s.', data, tag)
    return tag, datatype, ifd, data


def _tiff_set(source, output=None, setlist=None, unset=None, setfrom=None,
              overwrite=False, **kwargs):
    """
    Set or unset tags in a tiff file.

    :param source: the source path.
    :param output: the path to write.  Must not be the same as the source.
    :param setlist: a list of tuples of the form (tag, value), where tag is of
        the form <tag name or number>[:<datatype>][,<ifd-#>[,...]] and, if the
        datatype is not ASCII or binary, the value is a comma or whitespace
        separated list of values.  If value is prefixed by @, it is a path of a
        file containing the value.
    :param unset: a list of tags to unset of the form
        <tag name or number>[,<ifd-#>[,...]].
    :param setfrom: a list of tuples of the form (tag, tifffile), where tag is
        of the form <tag name or number>[,<ifd-#>[,...]].  The value will have
        the same datatype as the tifffile it is read from.
    :param overwrite: if False, throw an error if any of the ouput paths
        already exist.
    """
    info = read_tiff(source)
    if unset is not None:
        for tagspec in unset:
            tag, datatype, ifd, data = _tagspec_to_ifd(tagspec, info)
            if int(tag) not in ifd['tags']:
                logger.info('Tag %s is not present', tag)
            ifd['tags'].pop(int(tag), None)
    if setlist is not None:
        for tagspec, value in setlist:
            tag, datatype, ifd, data = _tagspec_to_ifd(tagspec, info, value)
            if data is not None:
                ifd['tags'][int(tag)] = {
                    'data': data,
                    'datatype': datatype,
                }
            else:
                logger.warning('Could not determine data for tag %s', tagspec)
    if setfrom is not None:
        for tagspec, tiffpath in setfrom:
            setinfo = read_tiff(tiffpath)
            tag, datatype, ifd, data = _tagspec_to_ifd(tagspec, info)
            if int(tag) not in setinfo['ifds'][0]['tags']:
                logger.warning('Tag %s is not in %s', tagspec, tiffpath)
            else:
                ifd['tags'][int(tag)] = setinfo['ifds'][0]['tags'][int(tag)]
    _apply_flags_to_ifd(info, **kwargs)
    write_tiff(info, output, allowExisting=overwrite)


def tiff_set(source, output=None, overwrite=False, setlist=None, unset=None,
             setfrom=None, **kwargs):
    """
    Set or unset tags in a tiff file.

    :param source: the source path.
    :param output: the path to write.  If not specified, rewrite the source
        path.  If the output is the same as the source, a temporary file is
        written and then the source file is updated.
    :param overwrite: if False, throw an error if any of the ouput paths
        already exist.
    :param setlist: a list of tuples of the form (tag, value), where tag is of
        the form <tag name or number>[:<datatype>][,<ifd-#>[,...]] and, if the
        datatype is not ASCII or binary, the value is a comma or whitespace
        separated list of values.  If value is prefixed by @, it is a path of a
        file containing the value.
    :param unset: a list of tags to unset of the form
        <tag name or number>[,<ifd-#>[,...]].
    :param setfrom: a list of tuples of the form (tag, tifffile), where tag is
        of the form <tag name or number>[,<ifd-#>[,...]].  The value will have
        the same datatype as the tifffile it is read from.
    """
    if output is None:
        output = source
    if os.path.exists(output) and not overwrite:
        raise TifftoolsException('File already exists: %s' % output)
    if os.path.realpath(source) == os.path.realpath(output) and source != '-':
        with tempfile.TemporaryDirectory('tifftools') as tmpdir:
            output = os.path.join(tmpdir, 'output.tiff')
            _tiff_set(source, output, setlist, unset, setfrom, **kwargs)
            with open(source, 'r+b') as fdest, open(output, 'rb') as fsrc:
                fdest.truncate(0)
                shutil.copyfileobj(fsrc, fdest)
    else:
        _tiff_set(source, output, setlist, unset, setfrom, overwrite=overwrite, **kwargs)


def main(args=None):
    from . import __version__

    if args is None:
        args = sys.argv[1:]
    description = 'Tiff tools to handle all tags and IFDs.  Version %s.' % __version__
    epilog = """All inputs can specify specific IFDs and sub-IFDs by
appending [,<IFD-#>[,[<tag-name-or-number>:]<SubIFD-#>[,<IFD-#>...]]
to the source path.  For instance, to only use the second IFD of sample.tiff,
use 'sample.tiff,1'."""
    argumentsForAllParsers = [{
        'args': ('--verbose', '-v'),
        'kwargs': dict(action='count', default=0, help='Increase output.'),
    }, {
        'args': ('--silent', '--quiet', '-q'),
        'kwargs': dict(action='count', default=0, help='Decrease output.'),
    }, {
        'args': ('--bigtiff', '-8'),
        'kwargs': dict(action='store_true', help='Output as bigtiff.'),
    }, {
        'args': ('--classic', '-4'),
        'kwargs': dict(
            dest='bigtiff', action='store_false', help='Output as classic tiff if small enough.'),
    }, {
        'args': ('--bigendian', '-B', '--big-endian', '--be'),
        'kwargs': dict(action='store_true', help='Output as big-endian.'),
    }, {
        'args': ('--littleendian', '-L', '--little-endian', '--le'),
        'kwargs': dict(dest='bigendian', action='store_false', help='Output as little-endian.'),
    }, {
        'args': ('--stop-on-warning', '-X'),
        'kwargs': dict(
            dest='warningIsError', action='store_true', help='Treat warnings as errors.'),
    }]
    mainParser = argparse.ArgumentParser(description=description, epilog=epilog)
    secondaryParser = argparse.ArgumentParser(description=description, add_help=False)
    subparsers = mainParser.add_subparsers(
        dest='command',
        title='subcommands',
        help='Subcommands.  See <subcommand> --help for details.')

    parserSplit = subparsers.add_parser(
        'split',
        help='split [--subifds] [--overwrite] source [prefix]',
        description='Split IFDs into separate files.',
        epilog=epilog)
    parserSplit.add_argument('source', help='Source file to split, - for stdin.')
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
        help='concat [--overwrite] source [source ...] output',
        description='Concatenate multiple files into a single TIFF.',
        epilog=epilog)
    parserConcat.add_argument(
        'source', nargs='+',
        help='Source files to concatenate, - for one file on stdin.')
    parserConcat.add_argument(
        'output', help='Output file, - for stdout.')
    parserConcat.add_argument(
        '--overwrite', '-y', action='store_true',
        help='Allow overwriting an existing output file.')

    parserInfo = subparsers.add_parser(
        'dump',
        aliases=['info'],
        help='dump [--max MAX] [--json] source [source ...]',
        description='Print contents of a TIFF file.',
        epilog=epilog)
    parserInfo.add_argument(
        'source', nargs='+', help='Source file.')
    parserInfo.add_argument(
        '--max', '-m', type=int, help='Maximum items to display.', default=20)
    parserInfo.add_argument(
        '--json', action='store_true',
        help='Output as json.')

    parserSet = subparsers.add_parser(
        'set',
        help='set source [--overwrite] [output] '
        '[--set TAG[:DATATYPE][,<IFD-#>] VALUE] [--unset TAG:[,<IFD-#>]] '
        '[--setfrom TAG[,<IFD-#>] TIFFPATH]',
        description='Set tags in a TIFF file.',
        epilog=epilog)
    parserSet.add_argument(
        'source', help='Source file, - for stdin.')
    parserSet.add_argument(
        '--overwrite', '-y', action='store_true',
        help='Allow overwriting an existing output file.')
    parserSet.add_argument(
        'output', nargs='?',
        help='Output file, - for stdout.  If no output file is specified, the '
        'source file is rewritten.')
    parserSet.add_argument(
        '--set', '-s', nargs=2, action='append', dest='setlist',
        metavar=('TAG[:DATATYPE][,<IFD-#>]', 'VALUE'),
        help='Set a tag.  The tag can be a case-insensitive name or integer, '
        'optionally with a case-insensitive datatype or a datatype integer.  '
        'Separate multiple numeric values with commas or whitespace.  '
        'Rational values must contain two integers for each entry.  ASCII '
        'values need to either be actual ASCII or Unicode; a terminating null '
        'byte is not required.  Specify "@PATH" for a value to load the value '
        'from a file.  Specify a specific IFD or sub-IFD by appending to the '
        'tag.  If no datatype is specified, the datatype will be determined '
        'from the known tag datatypes and inspection of the passed value.')
    parserSet.add_argument(
        '--unset', '-u', action='append',
        metavar=('TAG:[,<IFD-#>]', ),
        help='Unset a tag.  The tag can be a case-insensitive name or '
        'integer.')
    parserSet.add_argument(
        '--setfrom', '--set-from', '-f', nargs=2, action='append',
        metavar=('TAG[,<IFD-#>]', 'TIFFPATH'),
        help='Set a tag, reading the value from another TIFF file.')

    for parser in (secondaryParser, parserSplit, parserConcat, parserInfo, parserSet):
        for argument in argumentsForAllParsers:
            parser.add_argument(*argument['args'], **argument['kwargs'])

    # This allows argumentsForAllParsers to be either before or after the
    # command.
    secondary, notInSecondary = secondaryParser.parse_known_args(args)
    args = mainParser.parse_args(notInSecondary)
    for k, v in vars(secondary).items():
        setattr(args, k, v)
    logging.basicConfig(
        stream=sys.stderr, level=max(1, logging.WARNING - 10 * (args.verbose - args.silent)))
    logger.debug('Parsed arguments: %r', args)
    logLevelHandler = ThrowOnLevelHandler(
        level=logging.WARNING if args.warningIsError else logging.ERROR)
    try:
        logging.getLogger('tifftools').addHandler(logLevelHandler)
        if args.command:
            try:
                func = globals().get('tiff_' + args.command)
                func(**vars(args))
            except Exception as exc:
                if args.verbose - args.silent >= 1:
                    raise
                sys.stderr.write(str(exc).strip() + '\n')
                return 1
        else:
            mainParser.print_help(sys.stdout)
    finally:
        logging.getLogger('tifftools').handlers.remove(logLevelHandler)
