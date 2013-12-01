
from fabric.api import env
from fabtools import require
from . import scow_task


@scow_task
def setup_postgres(*args, **kwargs):
    #if 'db.setup_postgres' in env.machine.task_history_set
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
