
import os
from os import path
import tempfile
from fabric.api import local, cd, run, env
from fabtools import require


#def append_admin_profiles(content=''):
#    #fabric.contrib.files.append(
#    for admin in env.project.ADMINS:
       


class remote_local_file(object):
    """
    Context manager to tar and gzip a local file or directory, upload it
    to the remote host and remove it when the context finishes. Returns
    a path to the (un-tarred, un-gzipped) file/directory on the remote
    host.
    """
    def __init__(self, local_file):
        self.local_dirname, self.local_basename = path.split(local_file)

    def __enter__(self):
        # Wrap our local file in a temporary tarball
        f_descriptor, local_tarball_path = tempfile.mkstemp('.tgz')
        os.close(f_descriptor)
        tarball_basename = path.split(local_tarball_path)[1]
        tmp_dir_name = '.'.join(tarball_basename.split('.')[:-1])
        local('tar -zcf {outfile} -C {local_dir} {local_base}'.format(
            outfile=local_tarball_path,
            local_dir=self.local_dirname,
            local_base=self.local_basename))
        # Copy the tarball to the remote host
        require.files.directory('/tmp/' + tmp_dir_name)
        require.files.file(path.join('/tmp', tmp_dir_name, tarball_basename),
                           source=local_tarball_path)
        with cd(path.join('/tmp', tmp_dir_name)):
            run('tar -zxf ' + tarball_basename)
            run('rm ' + tarball_basename)
        self.remote_tmp_dir = path.join('/tmp', tmp_dir_name)
        return path.join(self.remote_tmp_dir, self.local_basename)

    def __exit__(self, typ, val, traceback):
        run('rm -Rf ' + self.remote_tmp_dir)
