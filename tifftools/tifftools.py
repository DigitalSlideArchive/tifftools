#!/usr/bin/env python3

import logging
import os
import struct

from .constants import Datatype, Tag, get_or_create_tag
from .path_or_fobj import OpenPathOrFobj, is_filelike_object

logger = logging.getLogger(__name__)


# IFD tags contain datatype, count, datapos, [offset], data, [ifds],
#   (key is tag number)
# IFD contains tags, path_or_fobj, size, tagcount, bigEndian, bigtiff, offset
# info (tifffile) contains endianPack, bigtiff, bigEndian, header (4 bytes),
#   firstifd, ifds, path_or_fobj, size


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

    :param path: the file to read.
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
            raise Exception('Not a known tiff header for %s' % path)
        info['bigEndian'] = header[:2] == b'MM'
        info['endianPack'] = bom = '>' if info['bigEndian'] else '<'
        info['bigtiff'] = b'\x2b' in header[2:4]
        if info['bigtiff']:
            offsetsize, zero, nextifd = struct.unpack(bom + 'HHQ', tiff.read(12))
            if offsetsize != 8 or zero != 0:
                raise Exception('Unexpected offset size')
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
    bom = info['endianPack']
    if not check_offset(info['size'], ifdOffset, 16 if info['bigtiff'] else 6):
        return
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
            taginfo['offset'] = data
        if tag in ifd['tags']:
            logger.warning('Duplicate tag %d: data at %d and %d' % (
                tag, ifd['tags'][tag]['datapos'], taginfo['datapos']))
        ifd['tags'][tag] = taginfo
    if info['bigtiff']:
        nextifd = struct.unpack(bom + 'Q', tiff.read(8))[0]
    else:
        nextifd = struct.unpack(bom + 'L', tiff.read(4))[0]
    read_ifd_tag_data(tiff, info, ifd, tagSet)
    ifdList.append(ifd)
    return nextifd


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
            taginfo['data'] = rawdata.rstrip(b'\x00').decode()
            # TODO: Handle null-separated lists
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


def write_tiff(ifds, path, bigEndian=None, bigtiff=None, allowExisting=False):
    """
    Write a tiff file based on data in a list of ifds.

    :param ifds: either a list of ifds, a single ifd record, or a read_tiff
        info record.
    :param path: output path.
    :param bigEndian: True for big endian, False for little endian, None for
        use the endian set in the first ifd.
    :param bigtiff: True for bigtiff, False for small tiff, None for use the
        bigtiff value in the first ifd.  If the small tiff is started and the
        file exceeds 4Gb, it is rewritten as bigtiff.  Note that this doesn't
        just convert to bigtiff, but actually rewrites the file to avoid
        unaccounted bytes in the file.
    :param allowExisting: if False, raise an error if the path already exists.
    """
    if isinstance(ifds, dict):
        bigEndian = ifds.get('bigEndian') if bigEndian is None else bigEndian
        bigtiff = ifds.get('bigtiff') if bigtiff is None else bigtiff
        ifds = ifds.get('ifds', [ifds])
    bigEndian = ifds[0].get('bigEndian', False) if bigEndian is None else bigEndian
    bigtiff = ifds[0].get('bigtiff', False) if bigtiff is None else bigtiff
    if not allowExisting and os.path.exists(path):
        raise Exception('File already exists')
    rewriteBigtiff = False
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
        for ifd in ifds:
            ifdPtr = write_ifd(dest, bom, bigtiff, ifd, ifdPtr)
            if not bigtiff and dest.tell() >= 2**32:
                rewriteBigtiff = True
                break
    if rewriteBigtiff:
        os.unlink(path)
        write_tiff(ifds, path, bigEndian, True)


def write_ifd(dest, bom, bigtiff, ifd, ifdPtr, tagSet=Tag):
    """
    Write an IFD to a TIFF file.  This copies iamge data from other tiff files.

    :param dest: the open file handle to write.
    :param bom: eithter '<' or '>' for using struct to encode values based on
        endian.
    :param bigtiff: True if this is a bigtiff.
    :param ifd: The ifd record.  This requires the tags dictionary and the
        path value.
    :param ifdPtr: a location to write the value of this ifd's start.
    :param tagSet: the TiffConstantSet class to use for tags.
    :return: the ifdPtr for the next ifd that could be written.
    """
    ptrpack = 'Q' if bigtiff else 'L'
    tagdatalen = 8 if bigtiff else 4
    ptrmax = 256 ** tagdatalen
    dest.seek(0, os.SEEK_END)
    ifdrecord = struct.pack(bom + ('Q' if bigtiff else 'H'), len(ifd['tags']))
    subifdPtrs = {}
    with OpenPathOrFobj(ifd['path_or_fobj'], 'rb') as src:
        for tag, taginfo in sorted(ifd['tags'].items()):
            tag = get_or_create_tag(
                tag, tagSet, **({'datatype': Datatype[taginfo['datatype']]}
                                if taginfo.get('datatype') else {}))
            if tag.isIFD() or taginfo.get('datatype') in (Datatype.IFD, Datatype.IFD8):
                if not len(taginfo.get('ifds', [])):
                    continue
                data = [0] * len(taginfo['ifds'])
                taginfo = taginfo.copy()
                taginfo['datatype'] = Datatype.IFD8 if bigtiff else Datatype.IFD
            else:
                data = taginfo['data']
            count = len(data)
            if tag.isOffsetData():
                if isinstance(tag.bytecounts, str):
                    data = write_tag_data(
                        dest, src, data,
                        ifd['tags'][int(tagSet[tag.bytecounts])]['data'],
                        ifd['size'])
                else:
                    data = write_tag_data(
                        dest, src, data, [tag.bytecounts] * count, ifd['size'])
                taginfo = taginfo.copy()
                taginfo['datatype'] = Datatype.LONG8 if bigtiff else Datatype.LONG
            if Datatype[taginfo['datatype']].pack:
                pack = Datatype[taginfo['datatype']].pack
                count //= len(pack)
                data = struct.pack(bom + pack * count, *data)
            elif Datatype[taginfo['datatype']] == Datatype.ASCII:
                # Handle null-seperated lists
                data = data.encode() + b'\x00'
                count = len(data)
            else:
                data = taginfo['data']
            tagrecord = struct.pack(bom + 'HH' + ptrpack, tag, taginfo['datatype'], count)
            if len(data) <= tagdatalen:
                if tag.isIFD() or taginfo.get('datatype') in (Datatype.IFD, Datatype.IFD8):
                    subifdPtrs[tag] = -(len(ifdrecord) + len(tagrecord))
                tagrecord += data + b'\x00' * (tagdatalen - len(data))
            else:
                if tag.isIFD() or taginfo.get('datatype') in (Datatype.IFD, Datatype.IFD8):
                    subifdPtrs[tag] = dest.tell()
                tagrecord += struct.pack(bom + ptrpack, dest.tell() % ptrmax)
                dest.write(data)
            ifdrecord += tagrecord
    pos = dest.tell()
    dest.seek(ifdPtr)
    dest.write(struct.pack(bom + ptrpack, pos % ptrmax))
    dest.seek(0, os.SEEK_END)
    dest.write(ifdrecord)
    nextifdPtr = dest.tell()
    dest.write(struct.pack(bom + ptrpack, 0))
    write_sub_ifds(dest, bom, bigtiff, ifd, pos, subifdPtrs)
    return nextifdPtr


def write_sub_ifds(dest, bom, bigtiff, ifd, parentPos, subifdPtrs, tagSet=Tag):
    """
    Write any number of SubIFDs to a TIFF file.  These can be based on tags
    other than the SubIFD tag.

    :param dest: the open file handle to write.
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
                    dest, bom, bigtiff, ifdInSubifd, nextSubifdPtr,
                    getattr(tag, 'tagset', None))
            subifdPtr += tagdatalen


def write_tag_data(dest, src, offsets, lengths, srclen):
    """
    Copy data from a source tiff to a destination tiff, return a list of
    offsets where data was written.

    :param dest: the destination file, opened to the location to write.
    :param src: the source file.
    :param offsets: an array of offsets where data will be copied from.
    :param lengths: an array of lengths to copy from each offset.
    :param srclen: the length of the source file.
    :return: the offsets in the destination file corresponding to the data
        copied.
    """
    COPY_CHUNKSIZE = 1024 ** 2

    if len(offsets) != len(lengths):
        raise Exception('Offsets and byte counts do not correspond.')
    destOffsets = [0] * len(offsets)
    # We preserve the order of the chunks from the original file
    offsetList = sorted([(offset, idx) for idx, offset in enumerate(offsets)])
    for offset, idx in offsetList:
        if offset:
            length = lengths[idx]
            if not check_offset(srclen, offset, length):
                continue
            src.seek(offset)
            destOffsets[idx] = dest.tell()
            while length:
                data = src.read(min(length, COPY_CHUNKSIZE))
                dest.write(data)
                length -= len(data)
    return destOffsets
