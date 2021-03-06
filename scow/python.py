
from os import path
from textwrap import dedent
import fabric
from fabric.api import env, run, cd, sudo
from fabric.context_managers import hide
from fabtools import require, git, files
from . import scow_task, require_dir


PYTHON_SRC_DIR = 'Python-{version}'
PYTHON_SOURCE_URL = 'http://www.python.org/ftp/python/{version}/' + PYTHON_SRC_DIR + '.tgz'
EZ_SETUP_URL = 'https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py'
PYENV_GIT_URL = 'git://github.com/yyuu/pyenv.git'

PYTHON_SYSTEM_PACKAGES = (
    #'uwsgi',
    'virtualenv',
    'virtualenvwrapper',
)


@scow_task
def setup_local_python_tools(*args, **kwargs):
    # Install easy_install and pip
    with hide('stdout'):
        run('wget {} -O - | python'.format(EZ_SETUP_URL))
    run('/usr/local/bin/easy_install pip')
    run('/usr/local/bin/pip install ' + ' '.join(PYTHON_SYSTEM_PACKAGES))
    venvwrapper_env_script = path.join(env.scow.CONFIG_DIR, 'venvwrapper-settings.sh')
    venvwrapper_dirs = {
        'workon_home': env.scow.VIRTUALENVWRAPPER_ENV_DIR,
        'project_home': env.scow.VIRTUALENVWRAPPER_PROJECT_DIR,
    }
    for venvwrapper_dir in venvwrapper_dirs.values():
        require_dir(venvwrapper_dir)
    require.files.file(
        venvwrapper_env_script,
        contents=dedent("""
            # Virtualenv wrapper settings used by django-scow
            export WORKON_HOME={workon_home}
            export PROJECT_HOME={project_home}
            export VIRTUALENVWRAPPER_HOOK_DIR={workon_home}
            export VIRTUALENVWRAPPER_LOG_DIR={workon_home}
            """.format(**venvwrapper_dirs)))

    fabric.contrib.files.append(
        '/etc/profile',
        dedent("""
        # Virtualenvwrapper shim [is this a shim?? what is a shim?] installed by scow
        . {}
        . /usr/local/bin/virtualenvwrapper.sh
        """.format(venvwrapper_env_script)),
    )


@scow_task
def setup_local_python(version=None, setup_tools=True):
    if env.machine.setup_local_python and not env.force:
        return

    version = version or env.project.PYTHON_VERSION
    python_src_dir = PYTHON_SRC_DIR.format(version=version)
    require.directory('$HOME/build-python')
    with cd('$HOME/build-python'):
        run('rm -Rf ./*')
        with hide('stdout'):
            run('wget ' + PYTHON_SOURCE_URL.format(version=version))
        run('tar -zxf ' + python_src_dir + '.tgz')
    with cd('$HOME/build-python/' + python_src_dir):
        run('./configure')
        run('make')
        run('make install')

    env.machine.setup_local_python = True
    if setup_tools:
        setup_local_python_tools()


@scow_task
def install_python_env():
    pyenv_exists = files.is_dir('/opt/pyenv')
    if not pyenv_exists or env.force:
        if pyenv_exists:
            sudo('rm -Rf /opt/pyenv')
        git.clone('https://github.com/yyuu/pyenv.git', '/opt/pyenv', use_sudo=True)
    
