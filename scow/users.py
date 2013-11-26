
from fabric.api import (
    env,
    #cd,
    #run,
    sudo,
    #settings,
)
#import fabtools
from fabtools import (
    require,
    user,
)
from . import (
    scow_task
)
from .exceptions import (
    UserDoesNotExistError,
    UserExistsError,
)
from .utils import get_admin_profile, remote_local_file


@scow_task
def create_admin(username, sudoer=True):
    """Create a system user account for a project admin"""
    if user.exists(username):
        raise UserExistsError("User already exists: " + username)
    admin = get_admin_profile(username)
    # TODO: Process more kwargs accepted by fabtools.require.user
    user_options = ('ssh_public_keys', 'shell',)
    user_kwargs = {kwarg: admin[kwarg] for kwarg in user_options if kwarg in admin}
    if 'skeleton_dir' in admin:
        with remote_local_file(admin['skeleton_dir']) as skel_dir:
            user_kwargs['skeleton_dir'] = skel_dir
            require.users.user(username, **user_kwargs)
    else:
        require.users.user(username, **user_kwargs)
    if sudoer:
        require.users.sudoer(username)
    #run_admin_postcreate(username)


#@scow_task
#def run_admin_postcreate(username):
#    """Run post-user-creation shell commands specified by an admin user."""
#    admin = get_admin_profile(username)
#    if 'post_create' in admin:
#        cmds = [line.strip() for line in admin['post_create'].splitlines() if line.strip()]
#        #with cd('~' + username):
#        with settings(shell='/bin/bash -l -c'):
#            for cmd in cmds:
#                sudo(cmd, user=username,
#                    #shell=False,
#                    #pty=False,
#            )


@scow_task
def create_missing_admins():
    """Create system accounts for any admins missing one"""
    for admin in env.project.ADMINS:
        if 'username' in admin and not user.exists(admin['username']):
            create_admin(admin['username'])


@scow_task
def delete_admin(username):
    """Remove a project admin's system account and home directory"""
    if not user.exists(username):
        raise UserDoesNotExistError("User does not exist: " + username)
    user_home = user.home_directory(username)
    sudo('deluser ' + username)
    sudo('rm -Rf ' + user_home)


@scow_task
def recreate_admin(username):
    """Delete and re-create the system account for a project user"""
    try:
        delete_admin(username)
    except UserDoesNotExistError:
        pass
    create_admin(username)
