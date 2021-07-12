from functools import wraps
from asyncio import run
from collections import OrderedDict, deque

def mutation(func):
    @wraps(func)
    def method(self, *arg, **kwargs):
        return func()
    return method


def action(func):
    async def method(self, *arg, **kwargs):
        return func()
    result = run(method)
    

class BaseModule:
    namespaced = False

    def __init__(self, **kwargs):
        self.state = deque()
        self.root_methods = kwargs.get('methods', {})

    def __call__(self, **kwargs):
        self.__init__(**kwargs)


class BaseStore(type):
    def __new__(cls, name, bases, attrs):
        new_class = super().__new__
        registered_modules = attrs.get('modules', [])
        if registered_modules:
            namespaced_modules = [
                (module.__name__.lower(), module()) for module in registered_modules 
                    if module.namespaced
            ]
            global_modules = [
                (module.__name__.lower(), module) for module in registered_modules
                    if not module.namespaced
            ]


            new_class = new_class(cls, name, bases, attrs)
            module_objects = {
                'private': OrderedDict(namespaced_modules),
                'public': OrderedDict(global_modules)
            }
            # We need to reiterate the global 
            # modules because they will be
            # receiving all the other modules
            for _, module in global_modules:
                module.root_methods = module_objects

            setattr(new_class, '_modules',  OrderedDict(**module_objects))
            return new_class
        return new_class(cls, name, bases, attrs)


class Store(metaclass=BaseStore):
    modules = []
    state = []
    history = deque()

    def get_module(self, name, namespaced=False) -> BaseModule:
        prefix = 'private' if namespaced else 'public'
        return self._modules.get(prefix).get(name, None)








# class SomeModule(BaseModule):
#     def add_another_value(self):
#         self.state.append()

# class SomeOtherModule(BaseModule):
#     namespaced = True

#     def add_some_value(self, value):
#         self.state.append(value)

# class MyStore(Store):
#     modules = []

#     # # @mutation
#     # def add_some_value(self):
#     #     self.state.append({'a': 1})

#     def initiate_empty_module(self, name, namespaced: bool = False):
#         new_class = type(name, (BaseModule,), {})
#         setattr(new_class, 'namespaced', namespaced)
#         self.modules.extend([new_class])
