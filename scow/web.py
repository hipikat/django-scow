
from fabric.api import env
from fabtools import require
from . import scow_task, db


DB_ENGINE_POSTGRES = 'django.db.backends.postgresql_psycopg2'


@scow_task
def setup_django_database(db_name, *args, **kwargs):
    if db['ENGINE'] == DB_ENGINE_POSTGRES:
        db.setup_postgres_database(db['NAME'] + env.scow.project_tag, db['USER'], db['PASSWORD'])
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
