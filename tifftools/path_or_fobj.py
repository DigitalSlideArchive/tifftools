#!/usr/bin/env python3

import contextlib
import shutil
import sys
import tempfile


def is_filelike_object(fobj):
    """
    Check if an object is file-like in that it has a read method.

    :param fobj: the possible filelike-object.
    :returns: True if the object is filelike.
    """
    return hasattr(fobj, 'read')


@contextlib.contextmanager
def OpenPathOrFobj(pathOrObj, mode='rb'):
    """
    Given any of a file path, a pathlib Path object, a filelike-object that is
    seekable, a filelike-object that is not seekable, or '-' or None to
    indicate either stdin or stdout, return a seekable filelike-object.

    :param pathOrObj: one of a file path, pathlib Path, filelike-object, or
        None or '-'.
    :param mode: the mode to open a path or temporary file as needed.  This
        won't affect a seekable filelike-object.  If '-' or None is specified,
        the presence of 'w' determines if stdout or stdin is opened (always in
        binary mode).
    :yields: a seekable filelike object.
    """
    if pathOrObj == '-' or pathOrObj is None:
        pathOrObj = sys.stdout.buffer if 'w' in mode.lower() else sys.stdin.buffer
    if not is_filelike_object(pathOrObj):
        with open(pathOrObj, mode) as fobj:
            yield fobj
    elif (hasattr(pathOrObj, 'seekable') and pathOrObj.seekable() and
            hasattr(pathOrObj, 'tell') and hasattr(pathOrObj, 'truncate')):
        yield pathOrObj
    elif 'w' not in mode.lower():
        # This doesn't use the TemporaryFile context manager, as it is useful
        # to have this temporary file exist after this context is finished and
        # allow it to be garbage-collected to close.
        fobj = tempfile.TemporaryFile('w+b')
        shutil.copyfileobj(pathOrObj, fobj)
        fobj.seek(0)
        yield fobj
    else:
        with tempfile.TemporaryFile('w+b') as fobj:
            yield fobj
            fobj.seek(0)
            shutil.copyfileobj(fobj, pathOrObj)
