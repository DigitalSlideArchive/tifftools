#!/usr/bin/env python3

import functools
import hashlib
import logging
import os
import shutil
import struct
import tempfile

from .constants import Datatype, Tag, get_or_create_tag
from .exceptions import MustBeBigTiffError, TifftoolsError
from .path_or_fobj import OpenPathOrFobj, is_filelike_object

logger = logging.getLogger(__name__)

_DEDUP_HASH_METHOD = 'sha1'


def check_offset(filelen, offset, length):
    """
    Check if a specific number of bytes can be read from a file at a given
    offset.

    :param filelen: the length of the file.
    :param offset: an absolute offset in the file.
    :param length: the number of bytes to read.
    :return: True if the offset and length are possible, false if not.
    """
    # The minimum offset is the length of the tiff header
    allowed = offset >= 8 and length >= 0 and offset + length <= filelen
    if not allowed:
        logger.warning(
            'Cannot read %d (0x%x) bytes from desired offset %d (0x%x).',
            length, length, offset, offset)
    return allowed


def read_tiff(path):
    """
    Read the non-imaging data from a TIFF and return a Python structure with
    the results.  The path may optionally be terminated with
    [,<IFD #>[,[<SubIFD tag name or number>:]<SubIFD #>[,<IFD #>...]]
    If a component is not specified, all of the IFDs from that level are used,
    e.g., ",1" will read IFD 1 and all subifds, ",1,0" or ",1:SubIFD:0" will
    read the chain of IFDs in the first SubIFD record, ",1,0,2" will read IFD 2
    from IFD 1's first SubIFD.

    The output is an "info" dictionary containing the following keys:
    - ifds: a list of ifd records
    - path_or_fobj: the path of the file or a file-like object referencing the
        tiff file.
    - size: the total length of the tiff file in bytes.
    - header: the first four bytes of the tiff file
    - bigEndian: True if big endian, False if little endian
    - bigtiff: True if bigtiff, False if classic
    - endianPack: the byte-ordering-mark for struct.unpack (either '<' or '>')
    - firstifd: the offset of the first IFD in the file.
    Each IFD is a dictionary containing the following keys:
    - offset: the offset of this ifd.
    - path_or_fobj, size, bigEndian, bigtiff: copied from the file's info
        dictionary.
    - tagcount: number of tags in the IFD
    - tags: a dictionary of tags in this IFD.  The keys are the integer tag
        values.
    Each IFD tag is a dictionary containing the following keys:
    - datatype: the Datatype of the tag
    - count: the number of elements in the tag.  For most numeric values, this
        is the total number of entries.  For RATIONAL and SRATIONAL, this is
        the number of pairs of entries.  For ASCII, this is the length in bytes
        including a terminating null.  For UNDEFINED, this is the length in
        bytes.
    - datapos: the offset within the file (always within the IFD) that the data
        or offset to the data is located.
    - [offset]: if the count is large enough that the data cannot be stored in
        the IFD, this is the offset within the file of the data associated with
        the tag.
    - [ifds]: if the tag contains sub-ifds, this is a list of lists of IFDs.

    :param path: the file or stream to read.
    :returns: a dictionary of information on the tiff file.
    """
    limitIFDs = None
    info = {
        'ifds': [],
    }
    if not is_filelike_object(path):
        for splits in range(1, len(str(path).split(','))):
            parts = str(path).rsplit(',', splits)
            if os.path.exists(parts[0]):
                limitIFDs = parts[1:]
                path = parts[0]
                break
    with OpenPathOrFobj(path, 'rb') as tiff:
        info['path_or_fobj'] = tiff if is_filelike_object(path) else path
        tiff.seek(0, os.SEEK_END)
        info['size'] = tiff.tell()
        tiff.seek(0)
        header = tiff.read(4)
        info['header'] = header
        if header not in (b'II\x2a\x00', b'MM\x00\x2a', b'II\x2b\x00', b'MM\x00\x2b'):
            raise TifftoolsError('Not a known tiff header for %s' % path)
        info['bigEndian'] = header[:2] == b'MM'
        info['endianPack'] = bom = '>' if info['bigEndian'] else '<'
        info['bigtiff'] = b'\x2b' in header[2:4]
        if info['bigtiff']:
            offsetsize, zero, nextifd = struct.unpack(bom + 'HHQ', tiff.read(12))
            if offsetsize != 8 or zero != 0:
                msg = 'Unexpected offset size'
                raise TifftoolsError(msg)
        else:
            nextifd = struct.unpack(bom + 'L', tiff.read(4))[0]
        info['firstifd'] = nextifd
        while nextifd:
            nextifd = read_ifd(tiff, info, nextifd, info['ifds'])
    logger.debug('read_tiff: %s', info)
    if limitIFDs:
        info, _ = read_tiff_limit_ifds(info, limitIFDs)
    return info


def read_tiff_limit_ifds(info, limitRecords, tagSet=Tag):
    """
    Based on a list of ifd limits, reduce the ifds returned.  The list
    alternates between <IFD #> and [tag number or name:]<SubIFD #>.

    :param info: tiff file information dictionary.
    :param limitRecords: a list of limit records.
    :param tagSet: the TiffConstantSet class to use for tags.
    :returns: tiff file information dictionary with reduced IFDs.
    :returns: tagSet: the tag set used in the last IFD.
    """
    if not limitRecords or not len(limitRecords):
        return info, tagSet
    ifd = info['ifds'][int(limitRecords[0])]
    if len(limitRecords) > 1:
        tagName, subIFDNum = 'SubIFD', limitRecords[1]
        if ':' in limitRecords[1]:
            tagName, subIFDNum = limitRecords[1].split(':', 1)
        tag = get_or_create_tag(tagName, tagSet)
        tagSet = tag.get('tagset')
        ifds = ifd['tags'][int(tag)]['ifds'][int(subIFDNum)]
    else:
        ifds = [ifd]
    info = info.copy()
    info['ifds'] = ifds
    info, tagSet = read_tiff_limit_ifds(info, limitRecords[2:], tagSet)
    info['ifdReduction'] = limitRecords
    return info, tagSet


def read_ifd(tiff, info, ifdOffset, ifdList, tagSet=Tag):
    """
    Read an IFD and any subIFDs.

    :param tiff: the open tiff file object.
    :param info: the total result structure.  Used to track offset locations
        and contains big endian and bigtiff flags.
    :param ifdOffset: byte location in file of this ifd.
    :param ifdList: a list that this ifd will be appended to.
    :param tagSet: the TiffConstantSet class to use for tags.
    """
    logger.debug(f'read_ifd: {ifdOffset} (0x{ifdOffset:X})')
    bom = info['endianPack']
    if not check_offset(info['size'], ifdOffset, 16 if info['bigtiff'] else 6):
        return None
    tiff.seek(ifdOffset)
    # Store the main path here.  This facilitates merging files.
    ifd = {
        'offset': ifdOffset,
        'tags': {},
        'path_or_fobj': info['path_or_fobj'],
        'size': info['size'],
        'bigEndian': info['bigEndian'],
        'bigtiff': info['bigtiff'],
    }
    if info['bigtiff']:
        ifd['tagcount'] = struct.unpack(bom + 'Q', tiff.read(8))[0]
    else:
        ifd['tagcount'] = struct.unpack(bom + 'H', tiff.read(2))[0]
    for _entry in range(ifd['tagcount']):
        if info['bigtiff']:
            tag, datatype, count, data = struct.unpack(bom + 'HHQQ', tiff.read(20))
            datalen = 8
        else:
            tag, datatype, count, data = struct.unpack(bom + 'HHLL', tiff.read(12))
            datalen = 4
        taginfo = {
            'datatype': datatype,
            'count': count,
            'datapos': tiff.tell() - datalen,
        }
        if datatype not in Datatype:
            logger.warning(
                'Unknown datatype %d (0x%X) in tag %d (0x%X)', datatype, datatype, tag, tag)
            continue
        if count * Datatype[taginfo['datatype']].size > datalen:
            if (tagSet and tag in tagSet and tagSet[tag].get('ndpi_offset') and (
                    not info.get('size') or info['size'] >= 0x100000000)):
                info['ndpi'] = True
                data = ifdOffset - ((ifdOffset - data) & 0xFFFFFFFF) if data < ifdOffset else data
            taginfo['offset'] = data
        if tag in ifd['tags']:
            logger.warning('Duplicate tag %d: data at %d and %d' % (
                tag, ifd['tags'][tag]['datapos'], taginfo['datapos']))
        ifd['tags'][tag] = taginfo
    if info['bigtiff'] or info.get('ndpi'):
        nextifd = struct.unpack(bom + 'Q', tiff.read(8))[0]
    else:
        nextifd = struct.unpack(bom + 'L', tiff.read(4))[0]
    read_ifd_tag_data(tiff, info, ifd, tagSet)
    ifdList.append(ifd)
    return nextifd


@functools.lru_cache(maxsize=10)
def memoize_rawdata(rawdata):
    """
    Deduplicate large chunks of repeated rawdata.

    If data is repeated, this will return a reference to the first instance,
    which will avoid allocating memory for each repetition.

    :param rawdata: an object to possibly deduplicate
    :returns: an equivalent object
    """
    return rawdata


def read_ifd_tag_data(tiff, info, ifd, tagSet=Tag):
    """
    Read data from tags; read subifds.

    :param tiff: the open tiff file object.
    :param info: the total result structure.  Used to track offset locations
        and contains big endian and bigtiff flags.
    :param ifd: the ifd record to get data for.
    :param tagSet: the TiffConstantSet class to use for tags.
    """
    bom = info['endianPack']
    for tag, taginfo in ifd['tags'].items():
        tag = get_or_create_tag(tag, tagSet)
        typesize = Datatype[taginfo['datatype']].size
        pos = taginfo.get('offset', taginfo['datapos'])
        if not check_offset(info['size'], pos, taginfo['count'] * typesize):
            return
        tiff.seek(pos)
        rawdata = tiff.read(taginfo['count'] * typesize)
        if Datatype[taginfo['datatype']].pack:
            taginfo['data'] = list(struct.unpack(
                bom + Datatype[taginfo['datatype']].pack * taginfo['count'], rawdata))
        elif Datatype[taginfo['datatype']] == Datatype.ASCII:
            try:
                taginfo['data'] = rawdata.rstrip(b'\x00').decode()
            except UnicodeDecodeError:
                taginfo['data'] = rawdata
            # TODO: Handle null-separated lists
        else:
            if len(rawdata) > 100000:
                taginfo['data'] = memoize_rawdata(rawdata)
            else:
                taginfo['data'] = rawdata
        if ((hasattr(tag, 'isIFD') and tag.isIFD()) or
                Datatype[taginfo['datatype']] in (Datatype.IFD, Datatype.IFD8)):
            taginfo['ifds'] = []
            subifdOffsets = taginfo['data']
            for subidx, subifdOffset in enumerate(subifdOffsets):
                subifdRecord = []
                taginfo['ifds'].append(subifdRecord)
                nextifd = subifdOffset
                while nextifd:
                    nextifd = read_ifd(
                        tiff, info, nextifd, subifdRecord, getattr(tag, 'tagset', None))
                    if subidx + 1 < len(subifdOffsets) and nextifd == subifdOffsets[subidx + 1]:
                        logger.warning('SubIFDs are double referenced')
                        break


def write_tiff(ifds, path, bigEndian=None, bigtiff=None, allowExisting=False,
               ifdsFirst=False, dedup=False):
    """
    Write a tiff file based on data in a list of ifds.

    The ifds or info record that is passed only needs a subset of the fields
    that are populated by read_tiff.  Specifically, if either bigEndian or
    bigtiff are None, their value istaken from either the main info dictionary,
    if passed, or the first IFD if not.  Otherwise, only the 'ifds' key is used
    in the info dictionary.  For each IFD, only the 'path_or_fobj' and 'tags'
    keys are used.  For IFD tags, either the 'ifds' or the 'datatype' and
    'data' tags are used.

    :param ifds: either a list of ifds, a single ifd record, or a read_tiff
        info record.
    :param path: output path or stream.
    :param bigEndian: True for big endian, False for little endian, None for
        use the endian set in the first ifd.
    :param bigtiff: True for bigtiff, False for small tiff, None for use the
        bigtiff value in the first ifd.  If the small tiff is started and the
        file exceeds 4Gb, it is rewritten as bigtiff.  Note that this doesn't
        just convert to bigtiff, but actually rewrites the file to avoid
        unaccounted bytes in the file.
    :param allowExisting: if False, raise an error if the path already exists.
    :param ifdsFirst: if True, write IFDs before their respective data.  When
        this is not set, data is stored (mixed tag and offset data),(ifd),
        (mixed tag and offset data),(ifd),...  When it is set, data is stored
        (ifd),(tag data),(ifd),(tag data),...,(offset data),(offset data),...
        This is not quite the COG specification, as that requires only the
        strip or tile offset data to be at the end, and that data to be ordered
        with the smallest image first, but if there are multiple conceptual
        images, each one in turn (e.g., level0,level1,level2,...,level0,level1,
        level2,...,...).
    :param dedup: if False, all data is written.  If True, data blocks that are
        identical are only written once.
    """
    if isinstance(ifds, dict):
        bigEndian = ifds.get('bigEndian') if bigEndian is None else bigEndian
        bigtiff = ifds.get('bigtiff') if bigtiff is None else bigtiff
        ifds = ifds.get('ifds', [ifds])
    bigEndian = ifds[0].get('bigEndian', False) if bigEndian is None else bigEndian
    bigtiff = ifds[0].get('bigtiff', False) if bigtiff is None else bigtiff
    finalpath = path
    if not is_filelike_object(path) and os.path.exists(path):
        if not allowExisting:
            msg = 'File already exists'
            raise TifftoolsError(msg)
        with tempfile.NamedTemporaryFile(
                prefix=os.path.basename(path), dir=os.path.dirname(path)) as temppath:
            path = temppath.name
    try:
        with OpenPathOrFobj(path, 'wb') as dest:
            bom = '>' if bigEndian else '<'
            header = b'II' if not bigEndian else b'MM'
            if bigtiff:
                header += struct.pack(bom + 'HHHQ', 0x2B, 8, 0, 0)
                ifdPtr = len(header) - 8
            else:
                header += struct.pack(bom + 'HL', 0x2A, 0)
                ifdPtr = len(header) - 4
            dest.write(header)
            origifdPtr = ifdPtr
            try:
                for datadest, ifddest in _ifdsPass(ifdsFirst, dest):
                    ifdPtr = origifdPtr
                    if bool(dedup):
                        dedup = {
                            'hashes': {}, 'reused': 0,
                            'hashlog': {} if not isinstance(dedup, dict) else
                            dedup.get('hashlog', {})}
                    for ifd in ifds:
                        ifdPtr = write_ifd(
                            datadest, ifddest, bom, bigtiff, ifd, ifdPtr,
                            ifdsFirst=ifdsFirst, dedup=dedup)
            except MustBeBigTiffError:
                # This can only be raised if bigtiff is false
                dest.seek(0)
                dest.truncate(0)
                write_tiff(ifds, dest, bigEndian, True, ifdsFirst=ifdsFirst, dedup=bool(dedup))
            else:
                if dedup and dedup['reused']:
                    logger.info('Deduplication reused %d block(s)', dedup['reused'])
    except BaseException:
        if path != finalpath:
            os.unlink(path)
        raise
    else:
        if path != finalpath:
            # By copying the tempfile to the existing destination, the target
            # path keeps its inode
            with open(finalpath, 'r+b') as fdest, open(path, 'rb') as fsrc:
                fdest.truncate(0)
                shutil.copyfileobj(fsrc, fdest)
            os.unlink(path)


class _WriteTracker():
    """
    Provide a class that simulates enough of a I/O class to track length and
    offset.
    """

    def __init__(self, pos):
        self.pos = self.len = pos

    def write(self, data):
        self.pos += len(data)
        if self.pos > self.len:
            self.len = self.pos

    def tell(self):
        return self.pos

    def seek(self, offset, whence=os.SEEK_SET):
        self.pos = (self.len if whence == os.SEEK_END else (
            self.pos if whence == os.SEEK_CUR else 0)) + offset


def _ifdsPass(ifdsFirst, dest):
    """
    To handle writing IFDs before or after their associated data, return a
    pair of pointers to handle writing data.  For writing IFDs after the data,
    these are the same.  We write the data, collecting the location of the
    output as we go.  For writing IFDs first, we take three passes.  On the
    first pass, we don't actually write any data, we just collect lengths so
    that we can allocate the appropriate space for the IFD.  For the second
    pass, we write the actual IFD using the correct offsets but don't write the
    data.  Lasttly, we write the actual data.

    :param ifdsFirst: if True, ifds are written before data.
    :param dest: the original destination I/O pointer.
    :yields: the data destination I/O pointer and the ifd destination I/O
        pointer.
    """
    if not ifdsFirst:
        yield dest, dest
    else:
        ifddest = _WriteTracker(0)
        yield _WriteTracker(dest.tell()), ifddest
        yield _WriteTracker(dest.tell() + ifddest.tell()), dest
        yield dest, _WriteTracker(0)


def _adjustTaginfoForNonBigtiff(bigtiff, taginfo):
    """
    If this isn't a bigtiff, check if a datatype is one that isn't supported
    by non-bigtiff and convert it to the smaller size if possible.

    :param bigtiff: True if this is a bigtiff.
    :param taginfo: the tag with the current datatype, possibly modified.
    """
    if not bigtiff and Datatype[taginfo['datatype']] in {
            Datatype.LONG8, Datatype.SLONG8}:
        if Datatype[taginfo['datatype']] == Datatype.LONG8 and all(
                x < 2**32 for x in taginfo['data']):
            taginfo['datatype'] = Datatype.LONG.value
        elif Datatype[taginfo['datatype']] == Datatype.SLONG8 and all(
                abs(x) < 2**31 for x in taginfo['data']):
            taginfo['datatype'] = Datatype.SLONG.value
        else:
            msg = 'There are datatypes that require bigtiff format.'
            raise MustBeBigTiffError(msg)


def _checkDataForNonBigtiff(bigtiff, data):
    """
    If this is not a bigtiff, check that all values in the data array can fit
    in a uint32 value.

    :param bigtiff: True if this is a bigtiff.
    :param data: an array of integers to check.
    """
    if not bigtiff and any(val for val in data if val >= 0x100000000):
        msg = 'The file is large enough it must be in bigtiff format.'
        raise MustBeBigTiffError(msg)


def _writeDeferredData(bigtiff, bom, dest, ifd, ifdrecord, deferredData):
    """
    We can write data from pairs of tags with bytecounts and offsets after we
    have written the offsets and bytecounts themselves.  This is tracked in the
    deferredData dictionary per tag.  The offsets tag entry contains
    information on how to write the data.  The bytecounts tag entry will hold
    the generated byte counts.  The dictionary contains information about where
    this tag data is written in the destination file or the ifdrecord; these
    are updated as needed.

    :param bigtiff: True if this is a bigtiff.
    :param bom: either '<' or '>' for using struct to encode values based on
        endian.
    :param dest: the open file handle to write.
    :param ifd: The ifd record.  This requires the tags dictionary and the
        path value.
    :param ifdrecord: the generated ifdrecord; this is returned, possibly in a
        modified version.
    :param deferredData: a dictionary of tags that need to be written at the
        new dest current location.
    :returns: the modified ifdrecord.
    """
    for ddata in deferredData.values():
        if 'write' in ddata:
            ddata['data'] = write_tag_data(*ddata['write'])
    for ddata in deferredData.values():
        tag = ddata['tag']
        taginfo = ddata.get('taginfo', ifd['tags'][int(tag)])
        data = ddata['data']
        _checkDataForNonBigtiff(bigtiff, data)
        pack = Datatype[taginfo['datatype']].pack
        count = len(data) // len(pack)
        data = struct.pack(bom + pack * count, *data)
        if 'ifdoffset' in ddata:
            ifdrecord = ifdrecord[:ddata['ifdoffset']] + data + \
                ifdrecord[ddata['ifdoffset'] + len(data):]
        else:
            opos = dest.tell()
            dest.seek(ddata['offset'])
            dest.write(data)
            dest.seek(opos)
    return ifdrecord


def write_ifd(datadest, ifddest, bom, bigtiff, ifd, ifdPtr, tagSet=Tag,  # noqa
              ifdsFirst=False, dedup=False):
    """
    Write an IFD to a TIFF file.  This copies image data from other tiff files.

    :param datadest: the open file handle to write offset data.
    :param ifddest: the open file handle to write ids and tag data.
    :param bom: either '<' or '>' for using struct to encode values based on
        endian.
    :param bigtiff: True if this is a bigtiff.
    :param ifd: The ifd record.  This requires the tags dictionary and the
        path value.
    :param ifdPtr: a location to write the value of this ifd's start.
    :param tagSet: the TiffConstantSet class to use for tags.
    :param ifdsFirst: if True, write IFDs before their respective data.
        Otherwise, IFDs are written after their data.  IFDs are always adjacent
        to their data.
    :param dedup: if False, all data is written.  Otherwise, a dictionary with
        'hashes' and 'reused', where 'hashes' is a dictionary with keys of
        hashed data that have been written and values of the offsets where it
        was written, and 'reused' is a count of data blocks that were
        deduplicated.
    :return: the ifdPtr for the next ifd that could be written.
    """
    ptrpack = 'Q' if bigtiff else 'L'
    tagdatalen = 8 if bigtiff else 4
    nextifdPtr = None
    ifdrecord = struct.pack(bom + ('Q' if bigtiff else 'H'), len(ifd['tags']))
    subifdPtrs = {}
    deferredData = {}
    ifdpos = ifddest.tell()
    if ifdsFirst:
        ifdlen = (
            len(ifdrecord) + (20 if bigtiff else 12) * len(ifd['tags']) + (8 if bigtiff else 4))
        ifddest.write(b'\x00' * ifdlen)
    with OpenPathOrFobj(ifd.get('path_or_fobj', False), 'rb') as src:
        for tag, taginfo in sorted(ifd['tags'].items()):
            tag = get_or_create_tag(
                tag, tagSet, **({'datatype': Datatype[taginfo['datatype']]}
                                if taginfo.get('datatype') else {}))
            if tag.isIFD() or taginfo.get('datatype') in (Datatype.IFD, Datatype.IFD8):
                data = [0] * len(taginfo['ifds'])
                taginfo = taginfo.copy()
                taginfo['datatype'] = Datatype.IFD8 if bigtiff else Datatype.IFD
            else:
                data = taginfo['data']
            count = len(data)
            if tag.isOffsetData():
                taginfo = taginfo.copy()
                taginfo['datatype'] = Datatype.LONG8 if bigtiff else Datatype.LONG
                if isinstance(tag.bytecounts, str):
                    if ifdsFirst:
                        deferredData[int(tagSet[tag.bytecounts])] = {
                            'tag': tagSet[tag.bytecounts],
                            'data': ifd['tags'][int(tagSet[tag.bytecounts])]['data'][:],
                        }
                        deferredData[int(tag)] = {
                            'tag': tag,
                            'data': data[:],
                            'write': (
                                datadest, src, data,
                                deferredData[int(tagSet[tag.bytecounts])]['data'],
                                ifd['size'], dedup),
                            'taginfo': taginfo,
                        }
                    else:
                        data = write_tag_data(
                            ifddest, src, data,
                            ifd['tags'][int(tagSet[tag.bytecounts])]['data'],
                            ifd['size'], dedup)
                else:
                    data = write_tag_data(
                        ifddest, src, data, [tag.bytecounts] * count,
                        ifd['size'], dedup)
                _checkDataForNonBigtiff(bigtiff, data)
            _adjustTaginfoForNonBigtiff(bigtiff, taginfo)
            if Datatype[taginfo['datatype']].pack:
                pack = Datatype[taginfo['datatype']].pack
                count //= len(pack)
                data = struct.pack(bom + pack * count, *data)
            elif Datatype[taginfo['datatype']] == Datatype.ASCII:
                # Handle null-seperated lists
                data = (data if isinstance(data, bytes) else data.encode()) + b'\x00'
                count = len(data)
            else:
                data = taginfo['data']
            tagrecord = struct.pack(bom + 'HH' + ptrpack, tag, taginfo['datatype'], count)
            if len(data) <= tagdatalen:
                if tag.isIFD() or taginfo.get('datatype') in (Datatype.IFD, Datatype.IFD8):
                    subifdPtrs[tag] = -(len(ifdrecord) + len(tagrecord))
                if int(tag) in deferredData:
                    deferredData[int(tag)]['ifdoffset'] = len(ifdrecord) + len(tagrecord)
                tagrecord += data + b'\x00' * (tagdatalen - len(data))
            else:
                # word alignment for tag position
                if ifddest.tell() % 2:
                    ifddest.write(b'\x00')
                h = None
                tpos = ifddest.tell()
                if tag.isIFD() or taginfo.get('datatype') in (Datatype.IFD, Datatype.IFD8):
                    subifdPtrs[tag] = tpos
                elif dedup:
                    hashkey = hash(data)
                    if hashkey in dedup['hashlog']:
                        h = dedup['hashlog'][hashkey]
                    else:
                        h = hashlib.new(_DEDUP_HASH_METHOD, data).digest()
                        dedup['hashlog'][hashkey] = h
                    if h in dedup['hashes']:
                        tpos = dedup['hashes'][h]
                    else:
                        dedup['hashes'][h] = tpos
                        h = None
                _checkDataForNonBigtiff(bigtiff, [tpos])
                tagrecord += struct.pack(bom + ptrpack, tpos)
                if int(tag) in deferredData:
                    deferredData[int(tag)]['offset'] = tpos
                if not dedup or h is None:
                    ifddest.write(data)
            ifdrecord += tagrecord
        ifdrecord = _writeDeferredData(bigtiff, bom, ifddest, ifd, ifdrecord, deferredData)
    _checkDataForNonBigtiff(bigtiff, [ifddest.tell(), datadest.tell()])
    pos = ifddest.tell()
    # ifds are expected to be on word boundaries
    if pos % 2:
        ifddest.write(b'\x00')
        pos = ifddest.tell()
    ifddest.seek(ifdPtr)
    ifddest.write(struct.pack(bom + ptrpack, ifdpos if ifdsFirst else pos))
    ifddest.seek(ifdpos if ifdsFirst else 0, os.SEEK_SET if ifdsFirst else os.SEEK_END)
    ifddest.write(ifdrecord)
    nextifdPtr = ifddest.tell()
    ifddest.write(struct.pack(bom + ptrpack, 0))
    ifddest.seek(0, os.SEEK_END)
    write_sub_ifds(datadest, ifddest, bom, bigtiff, ifd,
                   ifdpos if ifdsFirst else pos, subifdPtrs,
                   ifdsFirst=ifdsFirst, dedup=dedup)
    return nextifdPtr


def write_sub_ifds(datadest, ifddest, bom, bigtiff, ifd, parentPos, subifdPtrs,
                   tagSet=Tag, ifdsFirst=False, dedup=False):
    """
    Write any number of SubIFDs to a TIFF file.  These can be based on tags
    other than the SubIFD tag.

    :param datadest: the open file handle to write offset data.
    :param ifddest: the open file handle to write ifd and tag data.
    :param bom: eithter '<' or '>' for using struct to encode values based on
        endian.
    :param bigtiff: True if this is a bigtiff.
    :param ifd: The ifd record.  This requires the tags dictionary and the
        path value.
    :param parentPos: the location of the parent IFD used for relative storage
        locations.
    :param: subifdPtrs: a dictionary with tags as the keys and value with
        either (a) the absolute location to store the location of the first
        subifd, or (b) a negative number whose absolute value is added to
        parentPos to get the absolute location to store the location of the
        first subifd.
    :param ifdsFirst: if True, write IFDs before their respective data.
        Otherwise, IFDs are written after their data.  IFDs are always adjacent
        to their data.
    :param dedup: if False, all data is written.  Otherwise, a dictionary with
        'hashes' and 'reused', where 'hashes' is a dictionary with keys of
        hashed data that have been written and values of the offsets where it
        was written, and 'reused' is a count of data blocks that were
        deduplicated.
    """
    tagdatalen = 8 if bigtiff else 4
    for tag, subifdPtr in subifdPtrs.items():
        if subifdPtr < 0:
            subifdPtr = parentPos + (-subifdPtr)
        for subifd in ifd['tags'][int(tag)]['ifds']:
            if not isinstance(subifd, list):
                subifd = [subifd]
            nextSubifdPtr = subifdPtr
            for ifdInSubifd in subifd:
                nextSubifdPtr = write_ifd(
                    datadest, ifddest, bom, bigtiff, ifdInSubifd,
                    nextSubifdPtr, getattr(tag, 'tagset', None),
                    ifdsFirst=ifdsFirst, dedup=dedup)
            subifdPtr += tagdatalen


def write_tag_data(dest, src, offsets, lengths, srclen, dedup=False):
    """
    Copy data from a source tiff to a destination tiff, return a list of
    offsets where data was written.

    :param dest: the destination file, opened to the location to write.
    :param src: the source file.
    :param offsets: an array of offsets where data will be copied from.
    :param lengths: an array of lengths to copy from each offset.
    :param srclen: the length of the source file.
    :param dedup: if False, all data is written.  Otherwise, a dictionary with
        'hashes' and 'reused', where 'hashes' is a dictionary with keys of
        hashed data that have been written and values of the offsets where it
        was written, and 'reused' is a count of data blocks that were
        deduplicated.
    :return: the offsets in the destination file corresponding to the data
        copied.
    """
    COPY_CHUNKSIZE = 1024 ** 2

    if len(offsets) != len(lengths):
        msg = 'Offsets and byte counts do not correspond.'
        raise TifftoolsError(msg)
    destOffsets = [0] * len(offsets)
    # We preserve the order of the chunks from the original file
    offsetList = sorted([(offset, idx) for idx, offset in enumerate(offsets)])
    olidx = 0
    lastOffset = lastLength = lastOffsetIdx = None
    blocks = []
    desttell = dest.tell()
    while olidx < len(offsetList):
        offset, idx = offsetList[olidx]
        length = lengths[idx]
        if offset and check_offset(srclen, offset, length):
            # if a block repeats a previous block, continue the pattern
            if lastOffset == offset and lastLength == length:
                destOffsets[idx] = destOffsets[lastOffsetIdx]
                olidx += 1
                continue
            lastOffset, lastLength, lastOffsetIdx = offset, length, idx
            destOffsets[idx] = desttell
            if dedup:
                hashkey = (hash(getattr(src, 'name', src)), offset)
                if hashkey in dedup['hashlog']:
                    h = dedup['hashlog'][hashkey]
                else:
                    readlen = length
                    h = hashlib.new(_DEDUP_HASH_METHOD)
                    src.seek(offset)
                    while readlen:
                        data = src.read(min(readlen, COPY_CHUNKSIZE))
                        h.update(data)
                        readlen -= len(data)
                    h = h.digest()
                    dedup['hashlog'][hashkey] = h
                if h in dedup['hashes']:
                    hpos = dedup['hashes'][h]
                    destOffsets[idx] = hpos
                    dedup['reused'] += 1
                    length = 0
                else:
                    dedup['hashes'][h] = destOffsets[idx]
            # Group reads when possible; the biggest overhead is in the actual
            # read call
            if length:
                if len(blocks) and offset == blocks[-1][0] + blocks[-1][1]:
                    blocks[-1] = (blocks[-1][0], blocks[-1][1] + length)
                else:
                    blocks.append((offset, length))
                desttell += length
        olidx += 1
    for offset, length in blocks:
        src.seek(offset)
        while length:
            data = src.read(min(length, COPY_CHUNKSIZE))
            dest.write(data)
            length -= len(data)
    return destOffsets
