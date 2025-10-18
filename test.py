import doit

import sys

class MyTasks:
    def task_hello(self):
        return {
            'actions': ['echo Hello, World!'],
        }

    def _to_dict(self):
        return dict((name, getattr(self, name)) for name in dir(self))

sys.exit(doit.run(MyTasks()._to_dict()))
