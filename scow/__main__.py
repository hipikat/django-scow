
from . import scow_task, ubuntu, users, python


@scow_task
def init_droplet(*args, **kwargs):
    """Set up admin users and a web stack on the droplet"""
    ubuntu.upgrade_packages()
    ubuntu.install_packages()
    users.create_missing_admins()
    python.setup_local_python(env.project.PYTHON_VERSION)
    #setup_postgres()
    #setup_nginx()
    #setup_uwsgi_emperor()


@scow_task
def install_project(settings_class, *args, **kwargs):
    """Install the project. Requires settings_class, tag optional"""
    pass
    #setup_project_virtualenv(*args, **kwargs)
    #setup_django_databases(*args, **kwargs)
    #install_project_src(settings_class, *args, **kwargs)
    #ggset_project_settings_class(str(settings_class), *args, **kwargs)
