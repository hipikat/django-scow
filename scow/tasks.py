
#from collections import namedtuple

from os import path
#from textwrap import dedent

#import fabric
from fabric.api import (
    cd,
    env,
    run,
    #sudo,
    prefix,
)
from fabric.context_managers import hide
#from fabric.tasks import Task
#import fabtools
from fabtools import (
    #deb,
    files,
    require,
    #user,
    supervisor,
)
#from project_settings import PYTHON_VERSION
from . import (
    scow_task,
    PYTHON_SYSTEM_PACKAGES,
    PYTHON_SRC_DIR,
    PYTHON_SOURCE_URL,
    EZ_SETUP_URL,
    DB_ENGINE_POSTGRES,
    #PROJECT_SHARED_SECRET,
    #PROJECT_SHARED_SECRET_PUB,

    # Sub-tasks
    tend,
)
from .utils import (
    remote_local_file,
    get_admin_profile,
    #append_admin_profiles,
)


@scow_task
def share_secrets():
    pass
    #for secret_path in (
    #        env.project.PROJECT_SHARED_SECRET,
    #        env.project.PROJECT_SHARED_SECRET_PUB):
    #    secret_dir, secret_file = path.split(secret_path)
    #    put(secret_path, path.join(env.scow.dirs.ETC_DIR, secret_file))

    #require.files.template_file(
    #    os.path.join(env.scow.pro)
    #)
    #fabric.contrib.
    #require.files.template_file()



@scow_task
def setup_project_virtualenv(force=False, *args, **kwargs):
    run('deactivate', warn_only=True, quiet=True)
    run('rmvirtualenv ' + env.scow.project_tagged, warn_only=True, quiet=True)
    run('mkvirtualenv ' + env.scow.project_tagged)


@scow_task
def workon_venv_test(*args, **kwargs):
    with prefix('workon ' + env.scow.project_tagged):
        print run('pwd')
        print run('env | grep VIR')


@scow_task
def install_project_requirements(*args, **kwargs):
    with prefix('workon ' + env.scow.project_tagged):
        with hide('stdout'):
            # TODO: Wheel your requirements in
            run('pip install -r etc/requirements.txt')
        for lib_name, lib_url in env.project.PROJECT_LIBS.items():
            dest_path = path.join('lib', lib_name)
            if 'force' in kwargs and kwargs['force']:
                run('rm -Rf ' + dest_path, warn_only=True, quiet=True)
            with hide('stdout'):
                run('git clone {} {}'.format(lib_url, dest_path))
            if files.is_file(path.join(dest_path, 'setup.py')):
                #with hide('stdout'):
                run('pip install ' + dest_path)
            else:
                run('add2virtualenv ' + dest_path)


@scow_task
def project_post_install(*args, **kwargs):
    with prefix('workon ' + env.scow.project_tagged):
        # Run custom shell commands defined by the project
        if hasattr(env.project, 'POST_INSTALL'):
            for line in env.project.POST_INSTALL.splitlines():
                line.strip() and run(line.strip())


# TODO: Remove these project-specific deps
@scow_task
def project_database_init(*args, **kwargs):
    with prefix('workon ' + env.scow.project_tagged):
        run('DJANGO_SETTINGS_CLASS=Core python manage.py syncdb')
        run('python manage.py syncdb')
        for app in (
                'django_extensions',
                'feincms.module.medialibrary',
                'feincms.module.page',
                'elephantblog',
                'hipikat'):
            run('python manage.py migrate ' + app)
        run('python manage.py migrate')


@scow_task
def install_project_src(settings_class, *args, **kwargs):
    # TODO: from env.scow.DIRS import would be nice
    with prefix('workon ' + env.scow.project_tagged):
        prj_dir = env.scow.project_dir
        if kwargs.get('force', False):
            #run('rm -Rf ' + env.scow.PROJECT_SRC_DIR)
            run('rm -Rf ' + prj_dir)
        with hide('stdout'):
            run('git clone {} {}'.format(env.project.PROJECT_GIT_URL, prj_dir))
        with cd(prj_dir):
            run('setvirtualenvproject')
            run('add2virtualenv etc')
            run('add2virtualenv src')
    set_project_settings_class(str(settings_class), *args, **kwargs)
    project_post_install(*args, **kwargs)
    install_project_requirements(*args, **kwargs)
    project_database_init(*args, **kwargs)


@scow_task
def set_project_settings_class(settings_class, *args, **kwargs):
    # TODO: Abstract something
    #print('***ONE')
    require.directory(path.join(env.scow.dirs.VAR_DIR, 'env'))
    require.files.file(
        path.join(env.scow.dirs.VAR_DIR, 'env', 'DJANGO_SETTINGS_CLASS'),
        contents=str(settings_class))
    print('***TWO')
    #require.files.file(
    #        )


# TODO: uwsgi config template creation


@scow_task
def enable_app_server(*args, **kwargs):
    # require directory env.scow.project_var_dir exists, owner www-data
    proc_name = env.scow.project_tagged
    with prefix('workon ' + env.scow.project_tagged):
        uwsgi_bin = run('echo $VIRTUAL_ENV/bin/uwsgi')
        uwsgi_logfile = run('echo `cat $VIRTUAL_ENV/$VIRTUALENVWRAPPER_PROJECT_FILENAME`/var/log/uwsgi.log')
    web_user = 'www-data'
    uwsgi_cmd=' '.join('''
        {uwsgi_bin}
        --socket {socket_path}
        --module {wsgi_app_module}
        --uid {web_user}
        --master
        --logto {uwsgi_logfile}
        '''.format(
            #process_name=env.scow.project_tagged,
            uwsgi_bin=uwsgi_bin,
            socket_path=path.join(env.scow.project_var_dir, 'uwsgi.sock'),
            wsgi_app_module=env.project.WSGI_APP_MODULE,
            web_user=web_user,
            uwsgi_logfile=uwsgi_logfile,
        ).split())

    require.directory(env.scow.project_var_dir, owner=web_user)
    require.supervisor.process(
        proc_name,
        command=uwsgi_cmd,
        user=web_user,
    )
    supervisor.start_process(proc_name)


@scow_task
def init_droplet(*args, **kwargs):
    upgrade_deb_packages()
    install_deb_packages()
    create_missing_admins()
    setup_local_python()
    setup_postgres()
    setup_nginx()
    #setup_uwsgi_emperor()


@scow_task
def install_project(settings_class, *args, **kwargs):
    setup_project_virtualenv(*args, **kwargs)
    setup_django_databases(*args, **kwargs)
    install_project_src(settings_class, *args, **kwargs)
    #ggset_project_settings_class(str(settings_class), *args, **kwargs)
