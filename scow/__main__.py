
from os import path
from fabric.api import env, run, sudo, prefix
from fabric.contrib import files as fabric_files
import fabtools
from . import scow_task, pkgs, users, python, web, db


@scow_task
def init_droplet(*args, **kwargs):
    """Set up admin users and a web stack on the droplet"""
    pkgs.upgrade_packages()
    pkgs.install_packages()
    users.create_missing_admins()
    installed_admins = env.machine.installed_admins or []
    # TODO: Make sure this is done by functions in the users module too.
    bash_rc_lines = [line for line in env.scow.SCOW_SHELL_SETUP_STRING.splitlines() if line]
    for user in installed_admins + ['root']:
        admin_bash_rc = path.join(fabtools.user.home_directory(user), '.bashrc')
        run('touch ' + admin_bash_rc)
        for line in bash_rc_lines:
            fabric_files.append(admin_bash_rc, line)
    for line in bash_rc_lines:
        fabric_files.append('/etc/profile', line)

    python.install_python_env()
    if env.project.PYTHON_VERSION not in env.scow.pyenv_versions:
        sudo('pyenv install ' + env.project.PYTHON_VERSION)
        sudo('pyenv rehash')
        sudo('pyenv global ' + env.project.PYTHON_VERSION)
    #with prefix('pyenv global ):
    python.setup_local_python_tools()

    # TODO: Check ALLOW_SYSTEM_PYTHON, and whether the requested project
    # Python version matches the installed system version.
    #if not getattr(env.project, 'ALLOW_SYSTEM_PYTHON', False):
    #python.setup_local_python(env.project.PYTHON_VERSION)
    db.setup_postgres()
    web.setup_nginx()
    #setup_uwsgi_emperor()


@scow_task
def install_project(settings_class, *args, **kwargs):
    """Install the project. Requires settings_class, tag optional"""
    #setup_project_virtualenv(*args, **kwargs)
    #setup_django_databases(*args, **kwargs)
    #install_project_src(settings_class, *args, **kwargs)
    #ggset_project_settings_class(str(settings_class), *args, **kwargs)
