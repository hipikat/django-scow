
from os import path
from textwrap import dedent
import fabric
from fabric.api import env, run, cd
from fabtools import require
from . import scow_task


PYTHON_SRC_DIR = 'Python-{version}'
PYTHON_SOURCE_URL = 'http://www.python.org/ftp/python/{version}/' + PYTHON_SRC_DIR + '.tgz'
EZ_SETUP_URL = 'https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py'

PYTHON_SYSTEM_PACKAGES = (
    #'uwsgi',
    'virtualenv',
    'virtualenvwrapper',
)


@scow_task
def setup_local_python_tools(*args, **kwargs):
    # Install easy_install and pip
    run('wget {} -O - | /usr/local/bin/python'.format(EZ_SETUP_URL))
    run('/usr/local/bin/easy_install pip')
    env.scow.registry.LOCAL_PYTHON_INSTALLED = True
    run('/usr/local/bin/pip install ' + ' '.join(PYTHON_SYSTEM_PACKAGES))
    venvwrapper_env_script = path.join(env.scow.CONFIG_DIR, 'venvwrapper-settings.sh')
    require.files.file(
        venvwrapper_env_script,
        contents=dedent("""
            # Virtualenv wrapper settings used by django-scow
            export WORKON_HOME=/var/env
            export PROJECT_HOME=/opt
            """))

    fabric.contrib.files.append(
        '/etc/profile',
        dedent("""
        # Virtualenvwrapper shim [is this a shim?? what is a shim?] installed by scow
        . {}
        . /usr/local/bin/virtualenvwrapper.sh
        """.format(venvwrapper_env_script)),
    )


@scow_task
def setup_local_python(*args, **kwargs):
    if env.machine.LOCAL_PYTHON_INSTALLED and not scow.force:
        return

    python_src_dir = PYTHON_SRC_DIR.format(version=env.project.PYTHON_VERSION)
    require.directory('$HOME/build-python')
    with cd('$HOME/build-python'):
        run('rm -Rf ./*')
        run('wget ' + PYTHON_SOURCE_URL.format(version=env.project.PYTHON_VERSION))
        run('tar -zxf ' + python_src_dir + '.tgz')
    with cd('$HOME/build-python/' + python_src_dir):
        run('./configure')
        run('make')
        run('make install')

    setup_local_python_tools()
