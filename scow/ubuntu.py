

from fabric.api import env
from fabtools import require, deb
from . import scow_task

CORE_DEBIAN_PACKAGES = (
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


@scow_task
def update_index():
    """Update the Debian package index"""
    deb.update_index()


@scow_task
def upgrade_packages():
    """Upgrade Debian packages (with a fresh index)"""
    if update_index not in env.session.tasks_finished:
        update_index()
    deb.upgrade()


@scow_task
def install_packages():
    """Install packages required by scow, the project and admin users"""
    pkgs = set(CORE_DEBIAN_PACKAGES)
    # Add packages required by the project
    if hasattr(env.project, 'REQUIRE_DEB_PACKAGES'):
        pkgs = pkgs | set(env.project.REQUIRE_DEB_PACKAGES)
    # Add packages requested by admins
    for admin_profile in env.project.ADMINS:
        if 'require_deb_packages' in admin_profile:
            pkgs = pkgs | set(admin_profile['require_deb_packages'])

    to_install = sorted(list(pkgs))
    previously_installed = env.machine.installed_packages or []
    if previously_installed != to_install or env.force:
        require.deb.packages(pkgs)
        env.machine.installed_packages = to_install
