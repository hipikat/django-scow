

from fabric.api import env
from . import scow_task


@scow_task
def do_nothing(*args, **kwargs):
    env.machine.FooThings = 'BarThings'
    pass


@scow_task
def set_trace(*args, **kwargs):
    import pdb; pdb.set_trace() 
