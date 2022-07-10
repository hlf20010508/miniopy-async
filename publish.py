import os
import minio_async

os.system('python setup.py publish')
os.system('twine upload dist/miniopy-async-%s.tar.gz' %
          minio_async.__version__)
for file in os.listdir('miniopy_async.egg-info'):
    os.remove(os.path.join('miniopy_async.egg-info', file))
os.rmdir('miniopy_async.egg-info')
for file in os.listdir('dist'):
    os.remove(os.path.join('dist', file))
os.rmdir('dist')
