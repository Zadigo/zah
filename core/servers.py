from collections import OrderedDict
from functools import wraps
from typing import Callable

import werkzeug
from werkzeug import exceptions
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.wrappers import Request
from zah.template import get_template_backend
from zah.responses import Http404, HttpResponse
from zah.router.app import Router
from zah.settings import settings
from zah.template.context import RequestContext


class AppOptions:
    """Represents all the options and applications/
    components that are available within the project"""
    
    apps = OrderedDict()

    def __contains__(self, name):
        return name in self.apps

    def __getitem__(self, name):
        return self.apps[name]

    @property
    def has_store(self):
        from zah.store import Store
        
        instance = self.apps.get('store', None)
        if instance is None:
            return False
        return isinstance(instance, Store)

    @property
    def has_router(self):
        instance = self.apps.get('router', None)
        if instance is None:
            return False
        return isinstance(instance, Router)

    def new_app(self, app: type):
        """Adds a new application or component
        to the options"""
        # name = app.__name__.lower()
        name = app.verbose_name
        instance = app()
        self.apps.setdefault(name, instance)

    def has_app(self, name):
        return name in self.apps


class BaseServer:
    _routes = []
    _running = False
    has_router = False

    app_options = AppOptions()

    headers = {
        'Content-Type': 'text/html; charset=utf8'
    }
    
    def __call__(self, **kwargs):
        if not self._running:
            self.create(**kwargs)

    @classmethod
    def create(cls, host='127.0.0.1', port=5000, **kwargs):
        attrs = {'use_reloader': True, 'use_debugger': True} | kwargs
        instance = cls()
        instance._running = True
        werkzeug.run_simple(host, port, instance.app, **attrs)

    def _dispatch_request(self, request: Request):
        # Populate the context with all
        # the necessary elements (apps...)
        # before passing it to the template
        context = RequestContext(request)
        context.populate(apps=self.app_options)

        if self.app_options.has_router:
            router = self.app_options.apps.get('router')

            candidate, candidates = router.match(request.path)
            if not candidate:
                return Http404(response=None)

            view = candidate['view']
            # We receive tuple (request, template (str)) and the
            # reason for that is to allow the decorators to
            # eventually modify or analyze the requests.
            # _, template_to_render = view(request=request, context=context)
            http_response = view(request=request, context=context)
            if isinstance(http_response, exceptions.HTTPException):
                return http_response
            return http_response
        
        attrs = {'mimetype': 'text/html', 'headers': self.headers}
        template_to_render = get_template_backend().get_template('index.html')
        return HttpResponse(template_to_render.render(context))

    def _build_request(self, environ, start_response):
        request = Request(environ)

        # TODO: Load a set of middlewares
        # that can do something to the
        # request before it is dispatched

        response = self._dispatch_request(request)
        return response(environ, start_response)

    def app(self, environ, start_response):
        """Entrypoint for starting the webserver"""
        return self._build_request(environ, start_response)

    def use_component(self, component: type):
        if not isinstance(component, type):
            raise TypeError('Component should be a type')
        self.app_options.new_app(component)

    def add_route(self, path: str, view: Callable, name=None):
        if not self.app_options.has_router:
            raise ValueError('You need to implement a router before you can implement routes')
        
        router = self.app_options.apps.get('router')
        router.add_route(path, view, name)
        self._routes = router.urls

    def as_route(self, path: str, name: str = None):
        """A decorator that transforms a function into a route"""
        def view(func):
            # @wraps(func)
            # def inner(func):
            self.add_route(path, func, name)
        return view


class DevelopmentServer(BaseServer):
    @classmethod
    def create(cls, host='127.0.0.1', port=5000, **kwargs):
        from zah import server_configuration
        attrs = {'use_reloader': True, 'use_debugger': True} | kwargs
        new_instance = SharedDataMiddleware(cls.app, {'/static': server_configuration.STATIC_ROOT})
        werkzeug.run_simple(host, port, new_instance, **attrs)
