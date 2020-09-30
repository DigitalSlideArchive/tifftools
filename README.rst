======================================================
Tiff Tools |build-status| |codecov-io| |license-badge|
======================================================

Pure Python tools for reading and writing all TIFF IFDs, sub-IFDs, and tags.

Developed by Kitware, Inc. with funding from The National Cancer Institute.

Example
=======

.. code-block:: python

    import tifftools
    info = tifftools.read_tiff('photograph.tif')
    info['ifds'][0]['tags'][tifftools.Tag.ImageDescription.value] = {
        'data': 'A dog digging.',
        'datatype': tifftools.Datatype.ASCII
    }
    exififd = info['ifds'][0]['tags'][tifftools.Tag.EXIFIFD.value]['ifds'][0]
    exififd['tags'][tifftools.constants.EXIFTag.FNumber.value] = {
        'data': [54, 10],
        'datatype': tifftools.Datatype.RATIONAL
    }
    tifftools.write_tiff(info, 'photograph_tagged.tif')

Commands
========

``tifftools --help`` and ``tifftools <command> --help`` provide usage details.

- ``tifftools split [--subifds] [--overwrite] source [prefix]``: split a tiff file into separate files.  This is also available as the library function ``tifftools.tiff_split``.

- ``tifftools concat [--overwrite] source [source ...] output``: merge multiple tiff files together.  Alias: ``tifftools merge``.  This is also available as the library function ``tifftools.tiff_concat``.

- ``tifftools dump [--max MAX] [--json] source [source ...]``: print information about a tiff file, including all tags, IFDs, and subIFDs.  Alias: ``tifftool info``.  This is also available as the library function ``tifftools.tiff_dump``.

- ``tifftools set source [--overwrite] [output] [--set TAG[:DATATYPE][,<IFD-#>] VALUE] [--unset TAG:[,<IFD-#>]] [--setfrom TAG[,<IFD-#>] TIFFPATH]``: modify, add, or remove tags.  This is also available as the library function ``tifftools.tiff_set``.

Library Functions
=================

- read_tiff

- write_tiff

- Constants

- Tag

- Datatype

- get_or_create_tag

- EXIFTag, GPSTag, etc.

Purpose
=======

tifftools provides a library and a command line program for maniplulating TIFF files.  It can split multiple images apart, merge images together, set any tag in any IFD, and dump all IFDs and tags in a single command.  It only uses python standard library modules, and is therefore widely compatible.

Rationale
---------

There was a need to combine images from multiple TIFF files without altering the image data or losing any tag information.  Further, when changing tag values, it was essential that the old values were fully removed from the output.

The command line tools associated with libtiff are commonly used for similar purposes.  The libtiff command tools have significant limitations: ``tiffdump`` and ``tiffinfo`` require multiple commands to see information from all IFDs.  ``tiffset`` does not remove data from a file; rather it appends to the file to only reference new data, leaving the old values inside the file.  ``tiffsplit`` doesn't keep tags it doesn't recognize, loosing data.  ``tiffcp`` always reencodes images and will fail for compression types it does not know.

Likewise, there is a wide variety of EXIF tools.  For the most part, these only alter tags, usually by appending to the existing file.  ImageMagick's ``convert`` command also recompresses images as it combines them.

Many programs deal with both classic and BigTIFF.  Some will start writing a classic TIFF, but leave a small amount of unused space just after the file header.  If the file exceeds 4Gb, parts of the file are rewritten to convert it to a BigTIFF file, leaving small amounts of abandoned data within the file.

``tifftools`` fills this need.  All tags are copied, even if unknown.  Files are always rewritten so that there is never abandoned data inside the file.  ``tifftools dump`` shows information on all IFDs and tags.  Many of the command line options are directly inspired from libtiff.

``tifftools`` does NOT compress or decompress any image data.  This is not an image viewer.  If you need to recompress an image or otherwise manipulate pixel data, use libtiff or another library.

As an explicit example, with libtiff's ``tiffset``, tag data just gets dereferenced and is still in the file:

.. code-block:: bash

    $ grep 'secret' photograph.tif  || echo 'not present'
    not present
    $ tiffset -s ImageDescription "secret phrase" photograph.tif 
    $ tiffinfo photograph.tif | grep ImageDescription
      ImageDescription: secret phrase
    $ grep 'secret' photograph.tif  || echo 'not present'
    Binary file photograph.tif matches
    $ tiffset photograph.tif -s ImageDescription "public phrase"
    $ tiffinfo photograph.tif | grep ImageDescription
      ImageDescription: public phrase
    $ grep 'secret' photograph.tif  || echo 'not present'
    Binary file photograph.tif matches

Whereas, with ``tifftools``:

.. code-block:: bash

    $ grep 'secret' photograph.tif || echo 'not present'
    not present
    $ tifftools set -y -s ImageDescription "secret phrase" photograph.tif 
    $ tiffinfo photograph.tif | grep ImageDescription
      ImageDescription: secret phrase
    $ grep 'secret' photograph.tif || echo 'not present'
    Binary file photograph.tif matches
    $ tifftools set -y photograph.tif -s ImageDescription "public phrase"
    $ tiffinfo photograph.tif | grep ImageDescription
      ImageDescription: public phrase
    $ grep 'secret' photograph.tif || echo 'not present'
    not present

TIFF File Structure
===================

TIFF Files consist of one or more IFDs (Image File Directories).  These can
be located anywhere within the file, and are referenced by their absolute
position within the file.  IFDs can refer to image data but they can also
contain a collection of metadata (for instance, EXIF or GPS data).  Small
data values are stored directly in the IFD.  Bigger data values (such as
image data, longer string, or lists of numbers) are referenced by the IFD and
are stored elsewhere in the file.

In the simple case, a TIFF file may have a list of IFDs, each one referencing
the next.  However, a complex TIFF file, such as those used by some
Whole-Slide Image (WSI) microscopy systems, can have IFDs organized in a
branching structure, where some IFDs are in a list and some reference SubIFDs
with additional images.

TIFF files can have their primary data stored in either little-endian or
big-endian.  Offsets to data are store as absolute numbers inside a TIFF
file.  There are two variations: "classic" and "BigTIFF" which use 32-bits
and 64-bits for these offsets, respectively.  If the file size exceeds 4 Gb or
uses 64-bit integer datatypes, it must be written as a BigTIFF.

Limitations
===========

Unknown tags that are offsets and have a datatype other than IFD or IFD8
won't be copied properly, as it is impossible to distinguish integer data
from offsets given LONG or LONG8 datatypes.  This can be remedied by
defining a new ``TiffConstant`` record which contains a ``bytecounts`` entry
to instruct whether the offsets refer to fixed length data or should get the
length of data from another tag.

Because files are ALWAYS rewritten, ``tifftools`` is slower than libtiff's ``tiffset`` and most EXIF tools.


.. |build-status| image:: https://circleci.com/gh/DigitalSlideArchive/tifftools.png?style=shield
  :target: https://circleci.com/gh/DigitalSlideArchive/tifftools
  :alt: Build Status

.. |codecov-io| image:: https://img.shields.io/codecov/c/github/DigitalSlideArchive/tifftools.svg
  :target: https://codecov.io/gh/DigitalSlideArchive/tifftools
  :alt: codecov.io


.. |license-badge| image:: https://img.shields.io/badge/license-Apache%202-blue.svg
  :target: https://raw.githubusercontent.com/DigitalSlideArchive/tifftools/master/LICENSE
  :alt: License
