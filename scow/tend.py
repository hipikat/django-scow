
from . import scow_task
from fabtools import deb


@scow_task
def update_deb_index():
    """Update Debian package index"""
    deb.update_index()


@scow_task
def upgrade_deb_packages():
    """Upgrade Debian packages (with a fresh index)"""
    if update_deb_index not in env.tasks_completed:
        update_deb_index()
    deb.upgrade()
