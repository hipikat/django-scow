
#from collections import namedtuple

from os import path
from textwrap import dedent

import fabric
from fabric.api import cd, env, run, sudo, prefix
from fabric.context_managers import hide
#from fabric.tasks import Task
#import fabtools
from fabtools import (
    deb,
    files,
    require,
    user,
    supervisor,
)
from project_settings import PYTHON_VERSION
from . import (
    scow_task,
    CONFIG_DIR,
    DEBIAN_PACKAGES as CORE_DEBIAN_PACKAGES,
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
from .exceptions import (
    UserDoesNotExistError,
    UserExistsError,
)
from .utils import (
    remote_local_file,
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
def create_admin(username):
    if user.exists(username):
        raise UserExistsError("User already exists: " + username)
    for admin in env.project.ADMINS:
        if admin['username'] == username:
            break
    else:
        raise AttributeError("No dict with username {} in env.project.ADMINS (which should "
                             "be a list of dictionaries of admin profiles)".format(username))
    # Set up any ssh_public_keys and the shell, if set in the user's ADMINS dictionary
    # TODO: Process more kwargs accepted by fabtools.require.user
    user_options = ('ssh_public_keys', 'shell',)
    user_kwargs = {kwarg: admin[kwarg] for kwarg in user_options if kwarg in admin}
    if 'skeleton_dir' in admin:
        with remote_local_file(admin['skeleton_dir']) as skel_dir:
            user_kwargs['skeleton_dir'] = skel_dir
            require.users.user(username, **user_kwargs)
    else:
        require.users.user(username, **user_kwargs)
    require.users.sudoer(username)
    # Process lines in admin['post_create'] - without throwing up on error
    #if 'post_create' in admin:
    #    for line in admin['post_create'].splitlines():
    #        line.strip() and sudo(line.strip(), user=username)


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
def update_deb_packages():
    deb.update_index()


@scow_task
def upgrade_deb_packages():
    update_deb_packages()
    deb.upgrade()


@scow_task
def install_deb_packages():
    pkgs = set(CORE_DEBIAN_PACKAGES)
    # Add packages required by the project
    if hasattr(env.project, 'REQUIRE_DEB_PACKAGES'):
        pkgs = pkgs | set(env.project.REQUIRE_DEB_PACKAGES)
    # Add packages requested by admins
    for admin_profile in env.project.ADMINS:
        if 'requires_deb_packages' in 'admin_profile':
            pkgs = pkgs | set(admin_profile['requires_deb_packages'])
    require.deb.packages(pkgs)


@scow_task
def setup_local_python_tools(*args, **kwargs):
    # Install easy_install and pip
    run('wget {} -O - | /usr/local/bin/python'.format(EZ_SETUP_URL))
    run('/usr/local/bin/easy_install pip')
    env.scow.registry.LOCAL_PYTHON_INSTALLED = True
    run('/usr/local/bin/pip install ' + ' '.join(PYTHON_SYSTEM_PACKAGES))
    venvwrapper_env_script = path.join(CONFIG_DIR, 'venvwrapper-settings.sh')
    require.files.file(
        venvwrapper_env_script,
        contents=dedent("""
            # Virtualenv wrapper settings used by django-scow
            export WORKON_HOME=/var/env
            export PROJECT_HOME=/opt
            """))

    fabric.contrib.files.append(
        '/etc/profile',
        dedent("""
        # Virtualenvwrapper shim [is this a shim?? what is a shim?] installed by scow
        . {}
        . /usr/local/bin/virtualenvwrapper.sh
        """.format(venvwrapper_env_script)),
    )


@scow_task
def setup_local_python(*args, **kwargs):
    # Stop now if we've installed python and there's no `force` in kwargs
    if env.scow.registry.LOCAL_PYTHON_INSTALLED and (
            'force' not in kwargs or not kwargs['force']):
        return

    python_src_dir = PYTHON_SRC_DIR.format(version=PYTHON_VERSION)
    require.directory('$HOME/build-python')
    with cd('$HOME/build-python'):
        run('rm -Rf ./*')
        run('wget ' + PYTHON_SOURCE_URL.format(version=PYTHON_VERSION))
        run('tar -zxf ' + python_src_dir + '.tgz')
    with cd('$HOME/build-python/' + python_src_dir):
        run('./configure')
        run('make')
        run('make install')

    setup_local_python_tools()


@scow_task
def setup_postgres(*args, **kwargs):
    require.postgres.server()
    for admin in env.project.ADMINS:
        if 'username' in admin:
            require.postgres.user(admin['username'], 'insecure', superuser=True)
    require.postgres.user('root', 'insecure', superuser=True)


# TODO: Tangle with passwords properly
@scow_task
def setup_postgres_database(name, user, password, *args, **kwargs):
    require.postgres.server()
    require.postgres.user(user, 'insecure', superuser=True)
    require.postgres.database(name, user)


@scow_task
def setup_django_database(db, *args, **kwargs):
    if db['ENGINE'] == DB_ENGINE_POSTGRES:
        setup_postgres_database(db['NAME'] + env.scow.project_tag, db['USER'], db['PASSWORD'])
    else:
        raise NotImplementedError("Unknown database engine: " + db['ENGINE'])


@scow_task
def setup_django_databases(*args, **kwargs):
    for db in env.project.DATABASES.values():
        setup_django_database(db, *args, **kwargs)


@scow_task
def setup_nginx(*args, **kwargs):
    require.nginx.server()

    #TODO: delete sites-enabled/default

    #server_name = env.project.ROOT_FQDN
    #if 'server_suffix' in kwargs:
    #    server_name += '.' + kwargs['server_suffix']

    ##proxy_url = 'http://unix:/path/to/backend.socket:/uri/'

    #require.nginx.proxied_site(
    #    server_name=server_name,
    #    port=80,
    #    proxy_url=proxy_url,
    #)


#@scow_task
#def setup_uwsgi_emperor():


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
    create_missing_admins()
    upgrade_deb_packages()
    install_deb_packages()
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
