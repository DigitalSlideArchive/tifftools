import os
import runpy
import sys

import pytest

import tifftools

from .datastore import datastore


@pytest.mark.parametrize('cmd_params,check_text,catch_exc,test_path', [
    ([], 'subcommands', None, None),
    (['--help'], 'subcommands', SystemExit, None),
    (['info'], 'usage', SystemExit, None),
    (['info', '--help'], 'option', SystemExit, None),
    (['dump', '<input>'], 'Directory', None, 'aperio_jp2k.svs'),
    (['info', 'nosuchfile'], 'No such file', None, None),
])
def test_main(cmd_params, check_text, catch_exc, test_path, capsys):
    if test_path:
        path = datastore.fetch(test_path)
        cmd_params[cmd_params.index('<input>')] = path
    if catch_exc:
        with pytest.raises(catch_exc):
            tifftools.main(cmd_params)
    else:
        tifftools.main(cmd_params)
    captured = capsys.readouterr()
    assert check_text in captured.out or check_text in captured.err


@pytest.mark.parametrize('cmd_params,check_text,catch_exc,test_path', [
    ([], 'subcommands', None, None),
    (['--help'], 'subcommands', SystemExit, None),
    (['info'], 'usage', SystemExit, None),
    (['info', '--help'], 'option', SystemExit, None),
    (['dump', '<input>'], 'Directory', None, 'aperio_jp2k.svs'),
    (['info', 'nosuchfile'], 'No such file', SystemExit, None),
    (['info', os.path.join(
        os.path.dirname(__file__), 'data', 'bad_double_reference.tif')],
     '', None, None),
    (['info', '-X', os.path.join(
        os.path.dirname(__file__), 'data', 'bad_double_reference.tif')],
     'double referenced', SystemExit, None),
    (['info', '-X', '-v', os.path.join(
        os.path.dirname(__file__), 'data', 'bad_double_reference.tif')],
     '', Exception, None),
])
def test_main_module(cmd_params, check_text, catch_exc, test_path, capsys):
    if test_path:
        path = datastore.fetch(test_path)
        cmd_params[cmd_params.index('<input>')] = path
    oldsysargv = sys.argv[1:]
    sys.argv[1:] = cmd_params
    if catch_exc:
        with pytest.raises(catch_exc):
            runpy.run_module('tifftools', run_name='__main__', alter_sys=True)
    else:
        runpy.run_module('tifftools', run_name='__main__', alter_sys=True)
    sys.argv[1:] = oldsysargv
    captured = capsys.readouterr()
    assert check_text in captured.out or check_text in captured.err


def test_main_module_import(capsys):
    runpy.run_module('tifftools')
    captured = capsys.readouterr()
    assert 'subcommands' not in captured.out and 'subcommands' not in captured.err
