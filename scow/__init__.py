
#from contextlib import contextmanager
from os import path
from functools import wraps
from textwrap import dedent
#import posixpath

#import fabric
from fabric.api import (
    env,
    run,
    #prefix,
)
#from fabric.decorators import task
from fabric.tasks import Task, WrappedCallableTask
#import fabtools
from fabtools import require
from cinch.utils import FHSDirs


TOP_LEVEL_ENV = ('machine', 'session')


# TODO: Make these runtime-editable settings


def require_dir(remote_dir):
    """
    Require a remote directory to exist. This function wraps
    `fabtools.require.files.directory` so that it's only called on directories
    that haven't already been seen in this session.
    """
    if remote_dir not in env.session.seen_dirs:
        require.files.directory(remote_dir)
        env.session.seen_dirs.add(remote_dir)


class RemoteFilesystemCache(object):
    """
    An object that takes arbitrary attribute lookup and assignment,
    and retrieves/saves the values to files in a remote directory,
    simply using `eval()` and `repr()`.
    """
    def __init__(self, remote_dir, *args, **kwargs):
        """Ensure the cache directory exists."""
        require_dir(remote_dir)
        self.__dict__['cache_dir'] = remote_dir
        self.__dict__['open_attrs'] = {}
        #self.cache_dir = remote_dir
        #setattr(self, 'cache_dir', remote_dir)

    def __getattr__(self, name):
        """Read and evaluate a string from `name` in the cache directory."""
        #if name == 'cache_dir':
        #    return super(RemoteFilesystemCache, self).__getattribute__('cache_dir')
        #if hasattr(self, name):
        #    return super(self, RemoteFilesystemCache).__getattribute__(name)
        if name in self.__dict__:
            return self.__dict__[name]
        if name in self.open_attrs:
            return self.open_attrs[name]
        cache_dir = self.__dict__['cache_dir']
        val = run('cat ' + path.join(cache_dir, name), warn_only=True, quiet=True)
        return eval(val) if val.succeeded else None

    def __setattr__(self, name, val):
        """Write a stringified value to a file in the cache directory."""
        #import pdb; pdb.set_trace()
        #if name in self.open_attrs:
        self.open_attrs[name] = val
        #else:
        #    require.files.file(path.join(self.__dict__['cache_dir'], name), contents=repr(val))
        #    self.open_attrs[name] = val

    # TODO: Make this class able to act like a context manager?
    def write_all(self):
        for name, val in self.open_attrs.items():
            require.files.file(path.join(self.__dict__['cache_dir'], name), contents=repr(val))


class ScowSession(object):
    """
    General container for actions that have happened since fab was launched.
    """
    # List of directories we know exist on the remote end
    seen_dirs = set()
    # Stack of currently running task name strings
    task_stack = []
    # List of completed task name strings
    finished_tasks = []

    #@property
    #def tasks_started(self):
    #    return [task[1] for task in self.task_history if task[0] == 'started']

    #@property
    #def tasks_finished(self):
    #    return [task[1] for task in self.task_history if task[0] == 'finished']


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
    # Virtualenvwrapper's environment home (WORKON_HOME) directory
    VIRTUALENVWRAPPER_ENV_DIR = '/var/env'
    # Home for projects installed by scow
    VIRTUALENVWRAPPER_PROJECT_DIR = '/opt'

    @property
    def SCOW_SHELL_SETUP_STRING(self):
        return dedent("""
            # Source setup tasks required by scow:
            # - Set virtualenvwrapper directories
            source {scow_config_dir}/profile_tasks.sh
            """.format(scow_config_dir=self.CONFIG_DIR))

    @property
    def PROFILE_TASKS_SH_CONTENTS(self):
        scow_dirs = {
            'venv_env_dir': self.VIRTUALENVWRAPPER_ENV_DIR,
            'venv_prj_dir': self.VIRTUALENVWRAPPER_PROJECT_DIR,
        }
        return dedent("""
            # Set up standard scow machine environment
            export VIRTUALENVWRAPPER_ENV_DIR={venv_env_dir}
            export VIRTUALENVWRAPPER_PROJECT_DIR={venv_prj_dir}
            """.format(**scow_dirs))

    def __init__(self, *args, **kwargs):
        self.session = ScowSession()
        env.session = self.session

        self.machine = RemoteFilesystemCache(self.MACHINE_REGISTRY_DIR)
        env.machine = self.machine

        # Create easy direct-from-env access to objects commonly accessed from
        # tasks. Not too much, because namespaces are one honking great idea.
        #for top_level_attr in TOP_LEVEL_ENV:
        #    env[top_level_attr] = getattr(self, top_level_attr)

        if not self.machine.initialised or env.force:
            require_dir(self.APPS_VAR_DIR)
            require_dir(self.CONFIG_DIR)
            require.files.file(
                path.join(self.CONFIG_DIR, 'profile_tasks.sh'),
                contents=self.PROFILE_TASKS_SH_CONTENTS)

        self.machine.initialised = True

        super(ScowEnv, self).__init__(*args, **kwargs)


class ScowTask(Task):
    """Add local and remote project-related variables to Fabric's env."""

    def run(self, *args, **kwargs):
        if 'force' not in env:
            env.force = bool(kwargs.pop('force', False))
        if 'project' not in env:
            import project_settings
            env.project = project_settings
        if 'scow' not in env:
            env.scow = ScowEnv()

        env.project_tag = ('-' + str(kwargs.pop('tag'))) if 'tag' in kwargs else ''
        env.project_tagged = env.project.PROJECT_NAME + env.project_tag
        env.project_dir = path.join(env.scow.VIRTUALENVWRAPPER_PROJECT_DIR + env.project_tagged)

        env.local_project_dirs = env.project.DIRS
        env.remote_project_dirs = FHSDirs(env.project_dir)
        env.project_var_dir = path.join(env.scow.APPS_VAR_DIR, env.project_tagged)

        # TODO: Do something useful with this logging
        #env.session.task_history.append(('started', self.__name__))
        env.session.task_stack.append(self.__name__)
        print('>>>>>> task_stack: ' + str(env.session.task_stack))
        super(ScowTask, self).run(*args, **kwargs)
        env.session.finished_tasks.append(env.session.task_stack.pop())
        print('<<<<<< task_stack: ' + str(env.session.task_stack))
        if not env.session.task_stack:
            import pdb; pdb.set_trace()
            env.machine.write_all()
        #env.session.task_history.append(('finished', self.__name__))


def scow_task(*args, **kwargs):
    """Replacement `fabric.decorators.task`, which bases the task on ScowTask."""
    class ScowWrappedCallableTask(ScowTask, WrappedCallableTask, Task):
        pass

    invoked = bool(not args or kwargs)
    if not invoked:
        func, args = args[0], ()

    @wraps(func)
    def wrapper(func):
        return ScowWrappedCallableTask(func, *args, **kwargs)

    return wrapper if invoked else wrapper(func)


from .__main__ import init_droplet, install_project
# Silence PyFlake F401 warning (name imported but unused)
(init_droplet, install_project)
