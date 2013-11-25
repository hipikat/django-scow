
#from contextlib import contextmanager
from getpass import getuser
from os import environ, path
#import posixpath

#import fabric
from fabric.api import (
    env,
    run,
    #prefix,
)
#from fabric.decorators import task
from fabric.tasks import Task, WrappedCallableTask as FabricWrappedCallableTask
#import fabtools
from fabtools import require
from cinch.utils import FHSDirs

import project_settings


DEBIAN_PACKAGES = (
    # Essentials for building Python
    'build-essential',
    'libreadline-gplv2-dev',
    'libncursesw5-dev',
    'libssl-dev',
    'libsqlite3-dev',
    'tk-dev',
    'libgdbm-dev',
    'libc6-dev',
    'libbz2-dev',
    'libncurses5-dev',

    'postgresql-server-dev-9.1',

    'git',

    # TODO: Mechanism for enabling modules of machine configuration...
    # (currently packages in any ADMIN user's 'requires_deb_packages' profile
    # dict's key will get installed with init_droplet too).
    #'fail2ban',
)

PYTHON_SYSTEM_PACKAGES = (
    'uwsgi',
    'virtualenv',
    'virtualenvwrapper',
)

# TODO: Make these runtime-editable settings
PYTHON_SRC_DIR = 'Python-{version}'
PYTHON_SOURCE_URL = 'http://www.python.org/ftp/python/{version}/' + PYTHON_SRC_DIR + '.tgz'
EZ_SETUP_URL = 'https://bitbucket.org/pypa/setuptools/raw/bootstrap/ez_setup.py'
REGISTRY_DIR = '/var/local/scow/registry'
APPS_VAR_DIR = '/var/local/scow/apps'
CONFIG_DIR = '/etc/scow'
PROJECTS_DIR = '/opt'

DB_ENGINE_POSTGRES = 'django.db.backends.postgresql_psycopg2'


# TODO: Serious memoization?
class ScowRegistry(object):
    """
    Local host registry. The registry currently just stores files for variable
    names in /var/local/scow/registry/', and reads and writes their contents
    with Python's `eval()` and `repr()`, respectively. If a registry attribute
    hasn't been set, return `None`.
    """
    def __getattr__(self, name):
        reg_val = run('cat ' + path.join(REGISTRY_DIR, name), warn_only=True, quiet=True)
        return eval(reg_val) if reg_val.succeeded else None

    def __setattr__(self, name, val):
        require.files.file(path.join(REGISTRY_DIR, name), contents=repr(val))


class ScowEnv(object):
    registry = ScowRegistry()
    registry_dir = REGISTRY_DIR
    config_dir = CONFIG_DIR
    projects_dir = PROJECTS_DIR

    def __init__(self, *args, **kwargs):
        # Note that self will be the same object as env.scow
        require.files.directory(self.registry_dir)
        require.files.directory(self.config_dir)
        require.files.directory(self.projects_dir)
        #self.project_dir = path.join(self.projects_dir, self.project_tagged)
        #self.dirs = FHSDirs(self.project_dir)


class LazyScowEnv(object):
    """
    We need to prevent ScowEnv's init() from requiring the existence of
    REGISTRY_DIR before the environment's had time to load.
    """
    def _wake_scow_env(self, func=None, *attrs):
        env.scow = ScowEnv()
        global registry
        registry = env.scow
        if func:
            #import pdb; pdb.set_trace()
            return func(registry, *attrs)

    def __getattr__(self, name):
        return self._wake_scow_env(getattr, name)

    def __setattr__(self, name, val):
        return self._wake_scow_env(setattr, name, val)


env.scow = LazyScowEnv()
registry = env.scow


class ScowTask(Task):
    def __init__(self, *args, **kwargs):
        # TODO: Whaaaaat. Check we're not monkey-patching anything and remove?
        #reload(project_settings)
        #env.project = project_settings
        if 'project' not in env:
            env.project = project_settings

        # Change the user if there is a FABRIC_USER in project_settings
        # and it hasn't already been changed from the default (which would
        # typically be from a -u command line option).
        user_changed = lambda: False if env.user == getuser() else True
        if not user_changed() and hasattr(env.project, 'FABRIC_USER'):
            env.user = env.project.FABRIC_USER

        #if 'tag' in kwargs:
        #import pdb; pdb.set_trace()

        return super(ScowTask, self).__init__(*args, **kwargs)

    def get_admin_profile(self, username):
        for admin_profile in self.project.ADMINS:
            if admin_profile['username'] == username:
                return admin_profile
        raise AttributeError("No admin profile found with username: " + username)


class WrappedCallableTask(FabricWrappedCallableTask, ScowTask):
    def __init__(self, *args, **kwargs):
        #print("*** scow.WrappedCallableTask.__init__")
        return super(WrappedCallableTask, self).__init__(*args, **kwargs)

    def run(self, *args, **kwargs):
        """
        Do special env setup for ScowTasks here.
        """
        # project_tag[ged] should be used for, for instance:
        # database name, repo checkout name, config file name
        env.scow.project_tag = '-' + str(kwargs['tag']) if 'tag' in kwargs else ''
        env.scow.project_tagged = env.project.PROJECT_NAME + env.scow.project_tag

        env.scow.project_dir = path.join(env.scow.projects_dir, env.scow.project_tagged)
        env.scow.dirs = FHSDirs(env.scow.project_dir)
        env.scow.project_var_dir = path.join(APPS_VAR_DIR, env.scow.project_tagged)
        #import pdb; pdb.set_trace()

        super(WrappedCallableTask, self).run(*args, **kwargs)


def scow_task(*args, **kwargs):
    invoked = bool(not args or kwargs)
    task_class = kwargs.pop("task_class", WrappedCallableTask)
    if not invoked:
        func, args = args[0], ()

    def wrapper(func):
        return task_class(func, *args, **kwargs)

    return wrapper if invoked else wrapper(func)


#@contextmanager
#def virtualenvwrapper(env_name, local=False):
#    """
#    Context manager to activate an existing Python `virtual environment`_.
#
#    ::
#
#        from fabric.api import run
#        from fabtools.python import virtualenv
#
#        with virtualenv('/path/to/virtualenv'):
#            run('python -V')
#
#    .. _virtual environment: http://www.virtualenv.org/
#    """
#
#    path_mod = path if local else posixpath
#
#    #activate_path = path_mod.join(venv_path, 'bin', 'activate')
#
#    # Source the activation script
#    with prefix('. %s' % quote(activate_path)):
#        yield
