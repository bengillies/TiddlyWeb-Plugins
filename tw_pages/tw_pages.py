"""
TiddlyWebPages

by Ben Gillies
"""
import pdb
from tiddlyweb.model.bag import Bag
from tiddlyweb.model.recipe import Recipe
from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.store import Store, NoBagError

from tiddlyweb.web.handler.recipe import get_tiddlers
from tiddlyweb import control
from tiddlyweb.filters import parse_for_filters, recursive_filter
from tiddlyweb.serializations.html import Serialization as HTMLSerialization
from tiddlyweb.serializer import Serializer
from tiddlyweb.wikitext import render_wikitext
from tiddlywebplugins import replace_handler
from BeautifulSoup import BeautifulSoup

import logging
from jinja2 import Environment, FunctionLoader, Template
import re

BAG_OF_TEMPLATES = "templates"
BAG_OF_URLS = "urls"

def _extended_recipe_template(environ):
    """
    provide a means to specify custom {{ key }} values in recipes
    which are then replaced with the value specified in environ['recipe_extensions']
    """
    template = {}
    try:     
        if environ:
            template['user'] = environ['tiddlyweb.usersign']['name']
    except KeyError:
        pass
    extensions = environ.get('recipe_extensions') or {}
    for extension, value in extensions.iteritems():
        template[extension] = value
        
    return template
        
control._recipe_template = _extended_recipe_template

def _get_recipe(environ, recipe):
    """
    return the specified recipe from the store
    """
    store = environ['tiddlyweb.store']
    myRecipe = Recipe(recipe)
    myRecipe = store.get(myRecipe)
    
    return myRecipe



def register_urls(config, store):
    """
    get the custom urls specified out of the urls bag, register them
    with selector, and put them into environ ready for use.
    """
    #get the urls out of the store
    url_bag = Bag(BAG_OF_URLS)
    url_bag = store.get(url_bag)
    url_tiddlers = control.get_tiddlers_from_bag(url_bag)
    config['tw_pages_urls'] = {}
    for tiddler in url_tiddlers:
        #register the url with selector
        replacing = False
        for index, (regex, handler) in enumerate(config['selector'].mappings):
                if regex.match(tiddler.text) is not None:
                    replacing = True
                    config['selector'].mappings[index] = (regex, dict(GET=get_template))
        if not replacing:
            config['selector'].add(tiddler.text, GET=get_template)
        replacing = False
        
        #register the url in config
        try:
            recipe_str, filter_str = tiddler.fields['recipe_name'].split('?',1)
        except ValueError:
            filter_str = ''
            recipe_str = tiddler.fields['recipe_name']
            
        config['tw_pages_urls'][tiddler.text] = {
            'title': tiddler.title,
            'recipe': recipe_str,
            'filter': filter_str,
            'template': tiddler.fields['template']
        }
        
def register_templates(config, store):
    """
    get the templates out of the store, register them as extensions-
    types and serializers with TiddlyWeb, and put them into environ 
    ready for use.
    """
    #get the templates out of the store
    bag = Bag(BAG_OF_TEMPLATES)
    bag = store.get(bag)
    tiddlers = control.get_tiddlers_from_bag(bag)
    
    #register them in config
    config['tw_pages_serializers'] = {}
    for tiddler in tiddlers:
        try:
            extensionType = tiddler.fields.pop('mime_type')
        except KeyError:
            extensionType = 'application/twpages'
        if tiddler.title != 'Default':
            config['extension_types'][tiddler.title] = extensionType
        try:
            page_title = tiddler.fields.pop('page_title')
        except KeyError:
            page_title = None
        
        config['tw_pages_serializers'][tiddler.title] = {
            'title': page_title,
            'type': extensionType,
            'plugins': tiddler.fields,
            'template': tiddler.text
        }
    
    #finally, set the serializers
    config['serializers']['application/twpages'] = ['tw_pages','text/html; charset=UTF-8']
    config['serializers']['default'] = ['tw_pages','text/html; charset=UTF-8']
    config['serializers']['text/html'] = ['tw_pages','text/html; charset=UTF-8']

def register_config(config, store):
    """
    get the config tiddler out of the store,
    and put it in environ ready to use
    """
    #get the tiddler out of the store
    tiddler = Tiddler(config['tw_pages']['config'][1])
    tiddler.bag = config['tw_pages']['config'][0]
    tiddler = store.get(tiddler)
    
    #register it in environ
    config['tw_pages_config'] = {}
    settings = re.split('[\n\r]{2}', tiddler.text)
    for setting in settings:
        lines = setting.splitlines()
        curr_bag = ''
        for line in lines:
            key, value = re.split(':[ ]*', line, 1)
            if key == 'container':
                config['tw_pages_config'][value] = {}
                curr_bag = value
            else:
                config['tw_pages_config'][curr_bag][key] = value

def get_template(environ, start_response):
    """
    selector comes to this function when a custom url is found. 
    
    retrieve the recipe/serialization details and pass to 
    tiddlyweb.web.handler.recipe.get_tiddlers
    """
    #set url and extract variables
    url = environ['selector.matches'][0]
    patterned = len(environ['wsgiorg.routing_args'][1]) > 0 #are there variables to extract?
    if patterned:
        environ['recipe_extensions'] = {} 
        for element in environ['wsgiorg.routing_args'][1]:
            environ['recipe_extensions'][element] = environ['wsgiorg.routing_args'][1][element]

    #match the url with the appropriate entry in tw_pages_urls
    selector = environ['tiddlyweb.config']['selector']
    found = False
    for url_match in environ['tiddlyweb.config']['tw_pages_urls']:
        url_content = environ['tiddlyweb.config']['tw_pages_urls'][url_match]
        #check tiddler.text with selector to find out if it matches the url
        url_regex = selector.parser.__call__(url_match)
        if re.search(url_regex, url):
            url = url_match
            found = True
        if found:
            plugin_name = url_content['template']
            break
            
    #get any custom set filters and combine with any filters passed in via the query string
    if 'filter' in environ['tiddlyweb.config']['tw_pages_urls'][url]:
        filters = parse_for_filters(environ['tiddlyweb.config']['tw_pages_urls'][url]['filter'])[0]
        #strip duplicate filters
        filters = [custom_filter for custom_filter in filters if custom_filter.__name__ not in [environ_filter.__name__ for environ_filter in environ['tiddlyweb.filters']]]
        if len(environ['tiddlyweb.filters']) > 0:
            filters.extend(environ['tiddlyweb.filters'])
            
    #set up variables to pass into get_tiddlers
    environ['tiddlyweb.extension'] = str(plugin_name)
    environ['wsgiorg.routing_args'][1]['recipe_name'] = str(environ['tiddlyweb.config']['tw_pages_urls'][url]['recipe'])
    environ['tiddlyweb.filters'] = filters
    
    #set tiddlyweb.type to make sure we call the correct serializer
    try:
        mime_type = environ['tiddlyweb.config']['extension_types'][plugin_name]
    except KeyError:
        mime_type = 'default'
    environ['tiddlyweb.type'] = [mime_type]
    
    #set the title
    environ['tw_pages_title'] = environ['tiddlyweb.config']['tw_pages_urls'][url].get('title')
    
    return get_tiddlers(environ, start_response)


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
        def wikifier(mystr, path):
            """
            Render TiddlyWiki wikitext in the provided
            string to HTML. This function taken and modified
            from wikklytextrender.py
            """
            tiddler = Tiddler('tmp')
            tiddler.text = mystr
            tiddler.recipe = path
            return render_wikitext(tiddler, self.environ)
        def shorten(mystr, count):
            shortened_str = mystr[0:count]
            soup = BeautifulSoup(shortened_str)
            return soup.prettify()
        self.template_env.filters['wikified'] = wikifier
        self.template_env.filters['shorten'] = shorten
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
    
    def generate_index(self, content):
        """
        wrap up the HTML in <html> and <body> tags as specifed by
        the Default template, set the page title and provide a
        means to allow css and javascript files to be attached.
        """
        server_prefix = self.get_server_prefix()
        try:
            template = self.template_env.get_template(self.environ['tiddlyweb.config']['tw_pages_config'][self.environ['recipe_extensions']['bag']]['wrapper'])
        except KeyError:
            template = self.template_env.get_template('Default')
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

def refresh_urls(environ, start_response):
    """
    Provide a mechanism for somebody to update the URL list
    in selector without restarting apache. Entry point for
    selector from the url /admin/urls/refresh
    """
    start_response('200 OK', [
        ('Content-Type', 'text/html; charset=utf-8')
        ])
    register_urls(environ['tiddlyweb.config'], environ['tiddlyweb.store'])
    return "Your urls have been successfully updated"
    
def refresh_templates(environ, start_response):
    """
    Provide a mechanism for somebody to update the serialization 
    list in TiddlyWeb without restarting apache. Entry point for
    selector from the url /admin/templates/refresh
    """
    start_response('200 OK', [
        ('Content-Type', 'text/html; charset=utf-8')
        ])
    register_templates(environ['tiddlyweb.config'], environ['tiddlyweb.store'])
    return "Your templates have been successfully updated"

def refresh_config(environ, start_response):
    """
    Provide a mechanism for somebody to update the 
    default tw_pages config information in TiddlyWeb 
    without restarting apache. Entry point for
    selector from the url /admin/twpages/refresh
    """
    start_response('200 OK', [
        ('Content-Type', 'text/html; charset=utf-8')
        ])
    register_config(environ['tiddlyweb.config'], environ['tiddlyweb.store'])
    return "Your config has been successfully updated"

def init(config_in):
    """
    init function for tw_pages.
    Set URLs
    define serializers
    """
    config = config_in
    
    #provide a way to allow people to refresh their URLs
    config['selector'].add('/admin/urls/refresh', GET=refresh_urls)
    config['selector'].add('/admin/templates/refresh', GET=refresh_templates)
    config['selector'].add('/admin/twpages/refresh', GET=refresh_config)
                      
    #get the store
    store = Store(config['server_store'][0], {'tiddlyweb.config':config})

    #set the default config info
    if 'tw_pages' in config:
        if 'templates' in config['tw_pages']:
            BAG_OF_TEMPLATES = config['tw_pages']['templates']
        if 'urls' in config['tw_pages']:
            BAG_OF_URLS = config['tw_pages']['urls']
        if 'config' in config['tw_pages']:
            register_config(config, store)
    
    register_urls(config, store)
    register_templates(config, store)         
    
    
    
