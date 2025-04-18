import os
import shutil

from .datastore import datastore


def test_readme_code(tmp_path):
    os.mkdir(f'{tmp_path}/results')
    imagePath = datastore.fetch('d043-200.tif')
    readmePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../README.rst')
    data = open(readmePath).read()
    chunks = data.split('\n.. code-block:: python\n')[1:]
    for chunk in chunks:
        lines = chunk.split('\n')
        keep = []
        for line in lines:
            if line.strip() and not line.startswith('    '):
                break
            keep.append(line[4:])
        code = '\n'.join(keep).strip() + '\n'
        os.chdir(tmp_path)
        for dest in ['photograph.tif', 'photo1.tif', 'photo2.tif',
                     'photo3.tif', 'aerial_imagery.tif', 'mypic.tif']:
            shutil.copy(imagePath, dest)
        exec(code)
