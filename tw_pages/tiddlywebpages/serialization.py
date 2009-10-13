"""
TiddlyWebPages

by Ben Gillies
"""
from tiddlywebpages.filters import JINJA_FILTERS

from tiddlyweb.model.bag import Bag
from tiddlyweb.model.recipe import Recipe
from tiddlyweb.model.tiddler import Tiddler

from tiddlyweb.web.handler.recipe import get_tiddlers
from tiddlyweb import control
from tiddlyweb.filters import parse_for_filters, recursive_filter
from tiddlyweb.serializations.html import Serialization as HTMLSerialization
from tiddlyweb.serializer import Serializer

from jinja2 import Environment, FunctionLoader, Template
import re

def _get_recipe(environ, recipe):
    """
    return the specified recipe from the store
    """
    store = environ['tiddlyweb.store']
    myRecipe = Recipe(recipe)
    myRecipe = store.get(myRecipe)
    
    return myRecipe

class Serialization(HTMLSerialization):
    """
    generates HTML as specified depending on the extension 
    type given. Currently only works with list_tiddlers
    or tiddler_as. Can also pass tiddlers into other 
    serializations as and when required.
    """
    def return_jinja_template(self, template_name):
        """
        Returns the template as a string. used to pass into jinja
        """ 
        try:
            return self.environ['tiddlyweb.config']['tw_pages_serializers'][template_name]['template']
        except KeyError:
            return None

    def __init__(self, environ):
        self.environ = environ
        if 'tw_pages_title' in self.environ:
            self.page_title = self.environ.pop('tw_pages_title')
        else:
            self.page_title = ''
        self.plugin_name = ''
        if not self.environ.get('recipe_extensions'):
            self.environ['recipe_extensions'] = {}
        self.template_env = Environment(loader=FunctionLoader(self.return_jinja_template))
        for filter_name, filter_func in JINJA_FILTERS:
            self.template_env.filters[filter_name] = filter_func
        #put the query string into a dict (including filters so no tiddlyweb.query)
        query_splitter = lambda x: [t.split('=',1) for t in re.split('[&;]?', x)]
        try:
            self.query = dict(query_splitter(environ['QUERY_STRING']))
        except ValueError, KeyError:
            self.query = {}
    
    def tiddler_as(self, tiddler):
        """
        entry point for a single tiddler. Sets some variables
        and passes the tiddler into list_tiddlers for turning
        into HTML
        """
        if 'tiddler' not in self.environ['recipe_extensions']:
            self.environ['recipe_extensions']['tiddler'] = tiddler.title
        if 'bag' not in self.environ['recipe_extensions']:
            self.environ['recipe_extensions']['bag'] = tiddler.bag
        if tiddler.recipe and 'recipe' not in self.environ['recipe_extensions']:
            self.environ['recipe_extensions']['recipe'] = tiddler.recipe
            
        bag = Bag('tmpbag',tmpbag=True)
        bag.add_tiddler(tiddler)
        
        self.plugin_name = self.set_plugin_name('single_tiddler')
        
        if self.plugin_name not in self.environ['tiddlyweb.config']['tw_pages_serializers']:
            content = self.pass_through_external_serializer(self.plugin_name, tiddler)
            return content
            
        self.page_title = self.environ['tiddlyweb.config']['tw_pages_serializers'][self.plugin_name]['title'] or tiddler.title
        
        return self.list_tiddlers(bag)

    def list_tiddlers(self, bag):
        """
        takes a list of tiddlers in a bag (usually a tmpBag),
        and turns it into HTML depending on the extension type
        supplied.
        """
        base_tiddlers = bag.list_tiddlers()
        
        if type(base_tiddlers) != list:
            base_tiddlers = [t for t in base_tiddlers]
        try:   
            tiddler = base_tiddlers[0]
            if tiddler.recipe and 'recipe' not in self.environ['recipe_extensions']:
                self.environ['recipe_extensions']['recipe'] = tiddler.recipe
            if 'bag' not in self.environ['recipe_extensions'] and not bag.tmpbag:
                self.environ['recipe_extensions']['bag'] = bag.name 
            elif 'bag' not in self.environ['recipe_extensions']:
                self.environ['recipe_extensions']['bag'] = tiddler.bag
            if 'tiddler' not in self.environ['recipe_extensions']:
                self.environ['recipe_extensions']['tiddler'] = tiddler.title
        except IndexError:
            pass  
        
        self.plugin_name = self.set_plugin_name('list_tiddlers')
        
        try:
            self.plugins = self.environ['tiddlyweb.config']['tw_pages_serializers'][self.plugin_name]['plugins']
        except KeyError:
            self.plugins = {}
        
        if self.plugin_name not in self.environ['tiddlyweb.config']['tw_pages_serializers']:
            content = self.pass_through_external_serializer(self.plugin_name, base_tiddlers)
            return content
        
        if not self.page_title:
            self.page_title = self.set_page_title(self.environ['tiddlyweb.config']['tw_pages_serializers'][self.plugin_name]['title'] or self.plugin_name)
        else:
            self.page_title = self.set_page_title()
        
        content = self.generate_html(self.plugin_name, self.plugins, base_tiddlers)
        content = self.generate_index(content)
        
        return content 
    
    def generate_html(self, plugin_name, plugins, base_tiddlers):
        """
        recurse through the template stack and generate the HTML on the way back out.
        """
        plugin_html = {}
        if isinstance(plugins, dict):
            for template in plugins:
                recipe_data = plugins[template].split('?', 1)
                recipe = _get_recipe(self.environ, recipe_data[0])
                plugin_tiddlers = control.get_tiddlers_from_recipe(recipe, self.environ)
                if len(recipe_data) == 2:
                    filters = parse_for_filters(recipe_data[1])[0]
                    plugin_tiddlers = recursive_filter(filters, plugin_tiddlers)
                try:
                    plugin_plugins = self.environ['tiddlyweb.config']['tw_pages_serializers'][template]['plugins']
                    plugin_html[template] = self.generate_html(template, plugin_plugins, plugin_tiddlers)
                except KeyError:
                    #there is no plugin by that name, so try a (non TiddlyWebPages) serializer instead
                    plugin_html[template] = self.pass_through_external_serializer(template, plugin_tiddlers)
        server_prefix = self.get_server_prefix()
        try:
            template = self.template_env.get_template(plugin_name)
            content = template.render(base=base_tiddlers, extra=plugin_html, prefix=server_prefix, query=self.query, root_vars=self.environ['recipe_extensions'])
        except KeyError:
            content = self.pass_through_external_serializer(plugin_name, base_tiddlers)
        return content
    
    def get_wrapper_name(self):
        container = self.environ['recipe_extensions'].get('recipe', None) or self.environ['recipe_extensions'].get('bag')
        try:
            name = self.environ['tiddlyweb.config']['tw_pages_config'][container]['wrapper']
        except KeyError:
            name = self.environ['tiddlyweb.config']['tw_pages_serializers'][self.plugin_name]['wrapper']
        if not name:
            name = 'Default'
            
        return name
    
    def generate_index(self, content):
        """
        wrap up the HTML in <html> and <body> tags as specifed by
        the Default template, set the page title and provide a
        means to allow css and javascript files to be attached.
        """
        server_prefix = self.get_server_prefix()
        template = self.template_env.get_template(self.get_wrapper_name())
        return template.render(content=content, title=self.page_title, prefix=server_prefix)
    
    def get_server_prefix(self):
        """
        return the server_prefix from environ
        """
        if 'server_prefix' in self.environ['tiddlyweb.config']:
            server_prefix = self.environ['tiddlyweb.config']['server_prefix']
        else:
            server_prefix = ''
        return server_prefix
    
    def pass_through_external_serializer(self, name, tiddlers):
        """
        The specified template has not been found, so assume it
        is a different serializer that has ended up here due to
        content-type confusion, or has been specified as a sub-
        template within another template.

        Passes the serializer name into the Serializer base class
        so that it is rendered by the correct serializer and 
        returns the output.
        """
        serializer_module = self.environ['tiddlyweb.config']['serializers'].get(self.environ['tiddlyweb.config']['extension_types'].get(name))[0]
        serializer = Serializer(serializer_module, self.environ)
        
        if (type(tiddlers) != Tiddler):
            bag = Bag('tmpBag', tmpbag=True)
            bag.add_tiddlers(tiddlers)
        try:
            serializer.object = tiddlers
            return serializer.to_string()
        except AttributeError:
            return serializer.list_tiddlers(bag)
    
    def set_page_title(self, title=None):
        """
        returns the fully parsed page title, ready for output.
        """
        if title:
            new_title = title
        else:
            new_title = self.page_title
        for key, value in self.environ['recipe_extensions'].items():
            if key and value:
                new_title = new_title.replace('{{ ' + key + ' }}', value)
        return new_title
    
    def set_plugin_name(self, default_name):
        """
        sets the plugin name to be used based firstly on the extension,
        then on the default (as in tw_pages_config).
        
        nb - does nothing if plugin_name is already set
        """
        if not self.plugin_name:
            try:
                name = self.environ.get('tiddlyweb.extension') or self.environ['selector.matches'][0].rsplit('/',1)[1].rsplit('.',1)[1]
                if name not in self.environ['tiddlyweb.config']['tw_pages_serializers']:
                    raise IndexError
            except IndexError:
                try:
                    name = self.environ['tiddlyweb.config']['tw_pages_config'][self.environ['recipe_extensions'].get('recipe') or self.environ['recipe_extensions'].get('bag')][default_name]
                except KeyError:
                    name = self.environ['tiddlyweb.config']['tw_pages_serializers']['Default']['plugins'][default_name]
            return name
        return self.plugin_name