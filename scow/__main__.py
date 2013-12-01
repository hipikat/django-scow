
from os import path
from fabric.api import env
from fabric.contrib import files as fab_files
import fabtools
from . import scow_task, pkgs, users, python, web, db


@scow_task
def init_droplet(*args, **kwargs):
    """Set up admin users and a web stack on the droplet"""
    pkgs.upgrade_packages()
    pkgs.install_packages()
    python.install_python_env()
    users.create_missing_admins()
    installed_admins = env.machine.installed_admins or []
    for user in installed_admins + ['root']:
        fab_files.append(
            path.join(fabtools.user.home_directory(user), '.profile'),
            env.scow.SCOW_SHELL_SETUP_STRING)

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
    pass
    #setup_project_virtualenv(*args, **kwargs)
    #setup_django_databases(*args, **kwargs)
    #install_project_src(settings_class, *args, **kwargs)
    #ggset_project_settings_class(str(settings_class), *args, **kwargs)
