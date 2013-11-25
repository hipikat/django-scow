
from . import scow_task
from fabtools import deb


@scow_task
def update_deb_packages():
    """Update apt-get package index"""
    deb.update_index()


@scow_task
def upgrade_deb_packages():
    """Simple apt-get upgrade"""
    update_deb_packages()
    deb.upgrade()
