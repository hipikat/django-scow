
from fabric.api import env
from fabric.decorators import task
from fabric.tasks import Task, WrappedCallableTask as FabricWrappedCallableTask

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
    # TODO: Mechanism for enabling modules of machine configuration...
    # (currently packages in any ADMIN user's 'requires_deb_packages' profile
    # dict's key will get installed with init_droplet too).
    #'fail2ban',
)


class ScowTask(Task):
    def __init__(self, *args, **kwargs):
        from . import project_settings
        env.project = project_settings

        #if hasattr(self.project, 'PROJECT_USER'):
        #if 'PROJECT_USER' in self.project
        #if hasattr(getattr(self, ), 'PROJECT_USER':
        # Doi
        if hasattr(env.project, 'FABRIC_USER'):
            env.user = env.project.FABRIC_USER

        #print("*** scow.ScowTask.__init__")
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


def scow_task(*args, **kwargs):
    invoked = bool(not args or kwargs)
    task_class = kwargs.pop("task_class", WrappedCallableTask)
    if not invoked:
        func, args = args[0], ()

    def wrapper(func):
        return task_class(func, *args, **kwargs)

    return wrapper if invoked else wrapper(func)

