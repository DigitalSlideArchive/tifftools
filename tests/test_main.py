import pytest

import tifftools

from .datastore import datastore


@pytest.mark.parametrize('cmd_params,check_text,catch_exit,test_path', [
    ([], 'subcommands', False, None),
    (['--help'], 'subcommands', True, None),
    (['info'], 'usage', True, None),
    (['info', '--help'], 'optional arguments', True, None),
    (['dump', '<input>'], 'Directory', False, 'aperio_jp2k.svs'),
])
def test_main(cmd_params, check_text, catch_exit, test_path, capsys):
    if test_path:
        path = datastore.fetch(test_path)
        cmd_params[cmd_params.index('<input>')] = path
    if catch_exit:
        with pytest.raises(SystemExit):
            tifftools.main(cmd_params)
    else:
        tifftools.main(cmd_params)
    captured = capsys.readouterr()
    assert check_text in captured.out or check_text in captured.err
