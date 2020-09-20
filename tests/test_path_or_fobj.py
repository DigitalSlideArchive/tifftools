import io
import os
import pathlib
import sys

import pytest

from tifftools.path_or_fobj import OpenPathOrFobj, is_filelike_object


@pytest.mark.parametrize('obj,is_fobj', [
    ('-', False),
    (None, False),
    (os.path.realpath(__file__), False),
    (pathlib.Path(__file__), False),
    (sys.stdin.buffer, True),
    (sys.stdout.buffer, True),
    (io.BytesIO(), True),
])
def test_is_filelike_object(obj, is_fobj):
    assert is_filelike_object(obj) is is_fobj


def test_OpenPathOrFobj_file():
    with OpenPathOrFobj(__file__) as fobj:
        assert hasattr(fobj, 'seekable')


def test_OpenPathOrFobj_stdin(monkeypatch):
    mock_stdin = io.BytesIO()
    mock_stdin.write(b'This is a test')
    mock_stdin.seek(0)
    mock_stdin.seekable = lambda: False

    class Namespace(object):
        pass

    mock_obj = Namespace()
    mock_obj.buffer = mock_stdin
    monkeypatch.setattr('sys.stdin', mock_obj)
    with OpenPathOrFobj('-') as fobj:
        assert hasattr(fobj, 'seekable')
        fobj.seek(0)
        assert fobj.read() == b'This is a test'


def test_OpenPathOrFobj_stdout(capsys):
    with OpenPathOrFobj(None, 'wb') as fobj:
        assert hasattr(fobj, 'seekable')
        fobj.write(b'This is a test')
    captured = capsys.readouterr()
    assert captured.out == 'This is a test'


def test_OpenPathOrFobj_unseekable_write():
    unseekable = io.BytesIO()
    unseekable.seekable = lambda: False
    with OpenPathOrFobj(unseekable, 'wb') as fobj:
        assert hasattr(fobj, 'seekable')
        fobj.write(b'This is a test')
    assert unseekable.getvalue() == b'This is a test'
