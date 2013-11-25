
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

DB_ENGINE_POSTGRES = 'django.db.backends.postgresql_psycopg2'


def require_dir(remote_dir):
    """
    Require a remote directory to exist. This function wraps
    `fabtools.require.files.directory` so that it's only called on directories
    that haven't already been seen in this session.
    """
    if remote_dir not in env.session.seen_dirs:
        require.files.directory(remote_dir)
        env.session.seen_dirs.append(remote_dir)


class RemoteFilesystemCache(object):
    """
    An object that takes arbitrary attribute lookup and assignment,
    and retrieves/saves the values to files in a remote directory,
    simply using `eval()` and `repr()`.
    """
    def __init__(self, remote_dir, *args, **kwargs):
        require_dir(remote_dir)


class ScowSession(object):
    """
    General container for actions that have happened since fab was launched.
    """
    # List of directories we know exist on the remote end
    seen_dirs = set()


class ScowEnv(object):
    """
    The singleton env.scow object is an instance of this class, created the
    first time a ScowTask is called. This is the private namespace tasks,
    which TODOLipsum scow.tasks_completed

    To customise scow's behaviour, subclass this class and make it the default
    by somehow TODOLipsum

    Initialising this class adds several methods to the top-level env object.
    Should we work out a way to namespace them better?
    """
    #initialised = False

    # Contains files read/written on env.machine attribute access/assignment
    MACHINE_REGISTRY_DIR = '/var/local/scow/registry'
    # Variable files for apps (e.g. .sock files) live in APPS_VAR_DIR/app-name/
    APPS_VAR_DIR = '/var/local/scow/apps'
    # Configuration files used by scow on this machine
    CONFIG_DIR = '/etc/scow'
    # Home for projects installed by scow
    PROJECTS_DIR = '/opt'

    def __init__(self, *args, **kwargs):
        self.machine = RemoteFilesystemCache(self.MACHINE_REGISTRY_DIR)
        self.session = ScowSession()

        # Create easy direct-from-env access to objects commonly
        # accessed from tasks
        for top_level_attr in ('machine', 'session'):
            env[top_level_attr] = getattr(self, top_level_attr)

        super(ScowEnv, self).__init__(*args, **kwargs)
        





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
    """
    The singleton env.scow object is an instance of this class, created the
    first time a ScowTask is called. This is the private namespace tasks,
    which TODOLipsum scow.tasks_completed
    """
    initialised = False

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
        #if ['scow'] not in env:


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
    # If you specify a different task_class, we won't make sure that it's a
    # subclass of scow.WrappedCallableTask, since we're all consenting adults...
    # but if it doesn't implement the interface things WILL go wrong.
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
