"""
Define a class suitable for wrapping up a templating engine

(in this case, jinja)
"""
from tiddlywebpages.filters import TW_PAGES_FILTERS

from jinja2 import Environment, FunctionLoader, Template

class Template():            
    def __init__(self, environ):
        self.environ = environ
        self.template = None
        self.template_env = Environment(loader=FunctionLoader(self._get_template))
        for filter_name, filter_func in TW_PAGES_FILTERS:
            self.template_env.filters[filter_name] = filter_func
            
    def set_template(self, template_name):
        self.template = self.template_env.get_template(template_name)
        
    def render(self, **kwargs):
        return self.template.render(**kwargs)
        
    def _get_template(self, template_name):
        """
        Returns the template as a string. used to pass into jinja
        """ 
        try:
            return self.environ['tiddlyweb.config']['tw_pages_serializers'][template_name]['template']
        except KeyError:
            return None