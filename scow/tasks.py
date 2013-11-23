
from os import path
from fabric.api import cd, env, run, sudo, prefix
#from fabric.tasks import Task
from fabtools import (
    require,
    user,
)
from project_settings import PYTHON_VERSION
from . import (
    scow_task,
    DEBIAN_PACKAGES as CORE_DEBIAN_PACKAGES,
    PYTHON_SYSTEM_PACKAGES,
    PYTHON_SRC_DIR,
    PYTHON_SOURCE_URL,
    EZ_SETUP_URL,
    DB_ENGINE_POSTGRES,
)
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
    require.users.sudoer(username)


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
    # Install easy_install and pip
    run('wget {} -O - | /usr/local/bin/python'.format(EZ_SETUP_URL))
    run('/usr/local/bin/easy_install pip')
    env.scow.registry.LOCAL_PYTHON_INSTALLED = True
    run('/usr/local/bin/pip install ' + ' '.join(PYTHON_SYSTEM_PACKAGES))


@scow_task
def setup_postgres(name, user, password):
    require.postgres.server()
    require.postgres.user(user, password)
    require.postgres.database(name, user)


@scow_task
def setup_django_database(db):
    if db['ENGINE'] == DB_ENGINE_POSTGRES:
        setup_postgres(db['NAME'], db['USER'], db['PASSWORD'])
    else:
        raise NotImplementedError("Unknown database engine: " + db['ENGINE'])


@scow_task
def setup_django_databases():
    for db in env.project.DATABASES.values():
        setup_django_database(db)


@scow_task
def setup_nginx(*args, **kwargs):
    require.nginx.server()

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
def install_project(settings_class, tag=None, *args, **kwargs):
    print("in install_project-- " + str(env.scow.project_tagged))
    #import pdb; pdb.set_trace()
    pass


@scow_task
def setup_project():
    # TODO: Should reference tag
    import pdb; pdb.set_trace()
    #with prefix('workon ' + env.project.PROJECT_NAME):
    #    run('add2virtualenv src')
    #    run('add2virtualenv etc')


@scow_task
def install_project_libs(*args, **kwargs):
    # TODO: Should reference tag
    #with prefix('workon ' + env.scow.project_name_tagged):
    with prefix('workon ' + env.project.PROJECT_NAME):
        for lib_name, lib_url in env.project.PROJECT_LIBS.items():
            dest_path = path.join('lib', lib_name)
            if 'force' in kwargs and kwargs['force']:
                run('rm -Rf ' + dest_path, warn_only=True, quiet=True)
            run('git clone {} {}'.format(lib_url, dest_path))
            run('add2virtualenv ' + dest_path)


@scow_task
def init_droplet():
    create_missing_admins()
    install_deb_packages()
    setup_local_python()
    setup_django_databases()
    setup_nginx()
    #setup_uwsgi_emperor()
