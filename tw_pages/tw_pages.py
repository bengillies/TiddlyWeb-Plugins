"""
TiddlyWebPages

by Ben Gillies
"""

from tiddlyweb.model.bag import Bag
from tiddlyweb.model.recipe import Recipe
from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.store import Store, NoBagError

from tiddlyweb.web.wsgi import HTMLPresenter
from tiddlyweb import control
from tiddlyweb.filters import parse_for_filters, recursive_filter
from tiddlyweb.serializations.html import Serialization as HTMLSerialization
from tiddlyweb.serializer import Serializer
from tiddlywebplugins import replace_handler
from wikklytextrender import render as render_wikitext

import logging
from jinja2 import Environment, FunctionLoader, Template
import re

BAG_OF_TEMPLATES = "templates"
BAG_OF_URLS = "urls"

RECIPE_EXTENSIONS = {}

def _extended_recipe_template(environ):
    """
    provide a means to specify custom {{ key }} values in recipes
    which are then replaced with the value specified in RECIPE_EXTENSIONS
    """
    template = {}
    try:     
        if environ:
            template['user'] = environ['tiddlyweb.usersign']['name']
    except KeyError:
        pass
    for extension in RECIPE_EXTENSIONS:
        template[extension] = RECIPE_EXTENSIONS[extension]
        
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
            filter_str = tiddler.fields['filter']
        except KeyError:
            filter_str = ''
        config['tw_pages_urls'][tiddler.text] = {
            'title': tiddler.title,
            'recipe': tiddler.fields['recipe_name'],
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
        extensionType = tiddler.type or 'text/html'
        if tiddler.title != 'Default':
            config['extension_types'][tiddler.title] = extensionType
            config['serializers'][extensionType] = ['tw_pages','text/html; charset=UTF-8']
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
            if key == 'bag':
                config['tw_pages_config'][value] = {}
                curr_bag = value
            else:
                config['tw_pages_config'][curr_bag][key] = value

def get_template(environ, start_response):
    """
    selector comes to this function when a custom url is found. 
    
    Handle wsgiorg.routing_args and place in RECIPE_EXTENSIONS
    for later use. Find out which URL brought us into this 
    function using the parser in selector dn regex matching.
    
    Get the appropriate tiddlers out of the store and pass
    them into the Serialization class for processing.
    """
    #stage 1 = set url and extract variables
    url = environ['selector.matches'][0]
    patterned = len(environ['wsgiorg.routing_args'][1]) > 0 #are there variables to extract?
    if patterned: 
        for element in environ['wsgiorg.routing_args'][1]:
            RECIPE_EXTENSIONS[element] = environ['wsgiorg.routing_args'][1][element]

    #stage 2 = match the url with the appropriate entry in tw_pages_urls
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
            environ['tiddlyweb.config']
            plugin_name = url_content['template']
            break
    
    #stage 3 = get the tiddlers and pass them into the serializer        
    base_recipe = environ['tiddlyweb.config']['tw_pages_urls'][url]['recipe']
    recipe = _get_recipe(environ, base_recipe)
    tiddlers = control.get_tiddlers_from_recipe(recipe)
    
    #filter the tiddlers
    if 'filter' in environ['tiddlyweb.config']['tw_pages_urls'][url]:
        filters = parse_for_filters(environ['tiddlyweb.config']['tw_pages_urls'][url]['filter'])[0]
        #strip duplicate filters
        filters = [f for f in filters if f.__name__ not in [e.__name__ for e in environ['tiddlyweb.filters']]]
        if len(environ['tiddlyweb.filters']) > 0:
            filters.extend(environ['tiddlyweb.filters'])
        
        tiddlers = recursive_filter(filters, tiddlers)
    tiddlers = [t for t in tiddlers]
    

    serializer = Serialization(environ)
    
    if 'title' in environ['tiddlyweb.config']['tw_pages_urls'][url]:
        page_title = environ['tiddlyweb.config']['tw_pages_urls'][url]['title']
    serializer.page_title = page_title
    serializer.plugin_name = plugin_name
    
    bag = Bag('tmpbag',tmpbag=True)
    bag.add_tiddlers(tiddlers)
    content = serializer.list_tiddlers(bag)
    
    #stage 4 = return the content
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])    
    return content


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
        self.page_title = ''
        self.plugin_name = ''
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
        self.template_env.filters['wikified'] =wikifier
        #put the query string into a dict (including filters so no tiddlyweb.query)
        query_splitter = lambda x: [t.split('=',1) for t in re.split('[&;].', x)]
        try:
            self.query = dict(query_splitter(environ['QUERY_STRING']))
        except ValueError:
            self.query = {}
    
    def tiddler_as(self, tiddler):
        """
        entry point for a single tiddler. Sets some variables
        and passes the tiddler into list_tiddlers for turning
        into HTML
        """
        RECIPE_EXTENSIONS['tiddler'] = tiddler.title
        RECIPE_EXTENSIONS['bag'] = tiddler.bag
        if getattr(tiddler, 'recipe'):
            RECIPE_EXTENSIONS['recipe'] = tiddler.recipe
            
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
            if tiddler.recipe:
                RECIPE_EXTENSIONS['recipe'] = tiddler.recipe
            if 'bag' not in RECIPE_EXTENSIONS and not bag.tmpbag:
                RECIPE_EXTENSIONS['bag'] = bag.name 
            elif 'bag' not in RECIPE_EXTENSIONS:
                RECIPE_EXTENSIONS['bag'] = tiddler.bag
            if 'tiddler' not in RECIPE_EXTENSIONS:
                RECIPE_EXTENSIONS['tiddler'] = tiddler.title
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
            #we have come straight into list_tiddlers, so still need to set RECIPE_EXTENSIONS. Do this using the first tiddler in the list
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
                recipe = _get_recipe(self.environ, plugins[template])
                plugin_tiddlers = control.get_tiddlers_from_recipe(recipe)
                try:
                    plugin_plugins = self.environ['tiddlyweb.config']['tw_pages_serializers'][template]['plugins']
                    plugin_html[template] = self.generate_html(template, plugin_plugins, plugin_tiddlers)
                except KeyError:
                    #there is no plugin by that name, so try a (non TiddlyWebPages) serializer instead
                    plugin_html[template] = self.pass_through_external_serializer(template, plugin_tiddlers)
        server_prefix = self.get_server_prefix()
        try:
            template = self.template_env.get_template(plugin_name)
            content = template.render(base=base_tiddlers, extra=plugin_html, prefix=server_prefix, query=self.query)
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
            template = self.template_env.get_template(self.environ['tiddlyweb.config']['tw_pages_config'][RECIPE_EXTENSIONS['bag']]['wrapper'])
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
        serializer = Serializer(name, self.environ)
        if (type(tiddlers) != Tiddler):
            bag = Bag('tmpBag', tmpbag=True)
            bag.add_tiddlers(tiddlers)
            return serializer.list_tiddlers(bag)
        serializer.object = tiddlers
        return serializer.to_string()
    
    def set_page_title(self, title=None):
        """
        returns the fully parsed page title, ready for output.
        """
        if title:
            new_title = title
        else:
            new_title = self.page_title
        for key, value in RECIPE_EXTENSIONS.items():
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
                name = self.environ['selector.matches'][0].rsplit('/',1)[1].rsplit('.',1)[1]
                if name not in environ['tiddlyweb.config']['tw_pages_serializers']:
                    raise IndexError
            except IndexError:
                try:
                    name = self.environ['tiddlyweb.config']['tw_pages_config'][RECIPE_EXTENSIONS['bag']][default_name]
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
    
    
    
