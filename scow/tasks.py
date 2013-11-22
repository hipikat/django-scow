
from fabric.api import env, sudo
#from fabric.tasks import Task
from fabtools import (
    require,
    user,
)
from . import scow_task, DEBIAN_PACKAGES as CORE_DEBIAN_PACKAGES
from .exceptions import (
    UserDoesNotExistError,
    UserExistsError,
)
from .utils import remote_local_file


@scow_task
def create_admin(username):
    if user.exists(username):
        raise UserExistsError("User already exists: " + username)
    for admin in env.project.ADMINS:
        if admin['username'] == username:
            break
    else:
        raise AttributeError("No dict with username {} in env.project.ADMINS (which should "
                             "be a list of dictionaries of admin profiles)".format(username))
    # TODO: Process more kwargs accepted by fabtools.require.user
    user_options = ('ssh_public_keys', 'shell',)
    user_kwargs = {kwarg: admin[kwarg] for kwarg in user_options if kwarg in admin}
    if 'skeleton_dir' in admin:
        with remote_local_file(admin['skeleton_dir']) as skel_dir:
            user_kwargs['skeleton_dir'] = skel_dir
            require.users.user(username, **user_kwargs)
    else:
        require.users.user(username, **user_kwargs)


@scow_task
def create_missing_admins():
    for admin in env.project.ADMINS:
        if 'username' in admin and not user.exists(admin['username']):
            create_admin(admin['username'])


@scow_task
def delete_admin(username):
    if not user.exists(username):
        raise UserDoesNotExistError("User does not exist: " + username)
    user_home = user.home_directory(username)
    sudo('deluser ' + username)
    sudo('rm -Rf ' + user_home)


@scow_task
def recreate_admin(username):
    try:
        delete_admin(username)
    except UserDoesNotExistError:
        pass
    create_admin(username)


@scow_task
def install_deb_packages():
    pkgs = set(CORE_DEBIAN_PACKAGES)
    for admin_profile in env.project.ADMINS:
        if 'requires_deb_packages' in 'admin_profile':
            pkgs = pkgs | set(admin_profile['requires_deb_packages'])
    require.deb.packages(pkgs)


@scow_task
def init_droplet():
    create_missing_admins()
    install_deb_packages()


@scow_task
def deploy(host, settings_class="Production", user=None):
    if not user:
        #user = env.user
        # check project-user-config dictionary
        user = env.project.user
