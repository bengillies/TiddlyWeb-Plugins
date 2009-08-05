"""
TiddlyWebPages
     
Template tiddler format:

    tiddler.title = extension_type
    tiddler.type = content type
    tiddler.fields = sub-templates to include in template. Formatted as follows:
    
                tiddler.fields['plugin_name'] = 'recipe to use on plugin'
                where recipe is the name of the recipe

    tiddler.text = the template itself. layed out using Jinja2 templating syntax. 
    (nb - variables accessible within the template are: base (the base set of tiddlers); 
     and extra (a dict containing named sub-templates specified))
    
    There is a special template called "Default", which acts as a wrapper, wrapping up other templates 
    inside <html>/<body> tags, etc and providing a place to add scripts, stylesheets, rss feeds, and 
    whatever else you want to add to each page. It has two additional fields within it - single_tiddler
    and content_list: These let you specify which template to load up when you visit a single tiddler, 
    or the tiddlers in a bag/recipe.
        
URL pattern matching:

    Custom URLs can be extended by passing in custom variables. These can then be passed into custom
    recipes and titles - both the main recipe being loaded up at the URL, and the sub-recipe being 
    used by the templates. To use, add them into the URL path as follows:
    
        /url/path/{bag}/url/path/{tiddler}
        
    then, add them into the recipe/title in the appropriate places.
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
        replace_handler(config['selector'], tiddler.text, dict(GET=get_template))
        config['selector'].add(tiddler.text, GET=get_template)
        
        #register the url in config
        config['tw_pages_urls'][tiddler.text] = {
            'title': tiddler.title,
            'recipe': tiddler.fields['recipe_name'],
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
        if patterned:
            #check tiddler.text with selector to find out if it matches the url
            url_regex = selector.parser.__call__(url_match)
            if re.search(url_regex, url):
                url = url_match
                found = True
        elif url_match == url:
            found = True
        if found:
            environ['tiddlyweb.config']
            plugin_name = url_content['template']
            break
    
    #stage 3 = get the tiddlers and pass them into the serializer        
    base_recipe = environ['tiddlyweb.config']['tw_pages_urls'][url]['recipe']
    recipe = _get_recipe(environ, base_recipe)
    tiddlers = control.get_tiddlers_from_recipe(recipe)
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
        self.page_title = self.environ['tiddlyweb.config']['tw_pages_serializers'][self.plugin_name]['title'] or tiddler.title
        
        return self.list_tiddlers(bag)

    def list_tiddlers(self, bag):
        """
        takes a list of tiddlers in a bag (usually a tmpBag),
        and turns it into HTML depending on the extension type
        supplied.
        """
        if 'bag' not in RECIPE_EXTENSIONS and not bag.tmpbag:
            RECIPE_EXTENSIONS['bag'] = bag.name
        
        self.plugin_name = self.set_plugin_name('list_tiddlers')

        try:
            self.plugins = self.environ['tiddlyweb.config']['tw_pages_serializers'][self.plugin_name]['plugins']
        except KeyError:
            self.plugins = {}
        base_tiddlers = bag.list_tiddlers()
        
        if not self.page_title:
            #we have come straight into list_tiddlers, so still need to set RECIPE_EXTENSIONS. Do this using the first tiddler in the list
            if type(base_tiddlers) != list:
                base_tiddlers = [t for t in base_tiddlers]
            tiddler = base_tiddlers[0]
            if tiddler.recipe:
                RECIPE_EXTENSIONS['recipe'] = tiddler.recipe
            elif 'bag' not in RECIPE_EXTENSIONS:
                RECIPE_EXTENSIONS['bag'] = tiddler.bag
            if 'tiddler' not in RECIPE_EXTENSIONS:
                RECIPE_EXTENSIONS['tiddler'] = tiddler.title
            self.page_title = self.set_page_title(self.environ['tiddlyweb.config']['tw_pages_serializers'][self.plugin_name]['title'] or self.plugin_name)
        else:
            self.page_title = self.set_page_title()
        
        if self.plugin_name in self.environ['tiddlyweb.config']['tw_pages_serializers']:
            content = self.generate_html(self.plugin_name, self.plugins, base_tiddlers)
            content = self.generate_index(content)
        else:
            content = self.pass_through_external_serializer(self.environ, self.plugin_name, base_tiddlers)
        
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
            content = template.render(base=base_tiddlers, extra=plugin_html, prefix=server_prefix)
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
        bag = Bag('tmpBag', tmpbag=True)
        bag.add_tiddlers(tiddlers)
        return serializer.list_tiddlers(bag)
    
    def set_page_title(self, title=None):
        """
        returns the fully parsed page title, ready for output.
        """
        if title:
            new_title = title
        else:
            new_title = self.page_title
        for key, value in RECIPE_EXTENSIONS.items():
            self.page_title = self.page_title.replace('{{ ' + key + ' }}', value)
        return new_title
    
    def set_plugin_name(self, default_name):
        """
        sets the plugin name to be used based firstly on the extension,
        then on the default.
        
        nb - does nothing if plugin_name is already set
        """
        if not self.plugin_name:
            try:
                name = self.environ['selector.matches'][0].rsplit('/',1)[1].rsplit('.',1)[1]
            except IndexError:
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

def init(config_in):
    """
    init function for tw_pages.
    Set URLs
    define serializers
    """
    config = config_in
    
    #get the store
    store = Store(config['server_store'][0], {'tiddlyweb.config':config})
    
    #provide a way to allow people to refresh their URLs
    config['selector'].add('/admin/urls/refresh', GET=refresh_urls)
    config['selector'].add('/admin/templates/refresh', GET=refresh_templates)
    
    register_urls(config, store)
    register_templates(config, store)