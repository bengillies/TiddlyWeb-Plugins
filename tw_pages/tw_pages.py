"""
todo - dynamicise recipes and urls
     - implement other functions in the serializer (bag_as, recipe_as, etc)
     - allow overriding template files specified in plugins/serializers (maybe in the url tiddlers)
     - dynamicise page titles
     - script/stylesheet inclusion - add a "defaults" tiddler and provide a list for disabling it on certain tiddlers
     
Template tiddler format:

    tiddler.title = extension_type
    tiddler.type = content type
    tiddler.fields = sub-templates to include in template. Formatted as follows:
    
                tiddler.fields['plugin_name'] = 'recipe to use on plugin'
                where recipe is the name of the recipe

    tiddler.text = the template itself. layed out using Jinja2 templating syntax. 
    (nb - variables accessible within the template are: 
        base (the base set of tiddlers); and extra (a dict containing named sub-templates specified))
"""

from tiddlyweb.model.bag import Bag
from tiddlyweb.model.recipe import Recipe
from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.store import Store, NoBagError

from tiddlyweb.web.wsgi import HTMLPresenter
from tiddlyweb import control
from tiddlyweb.filters import parse_for_filters, recursive_filter

import logging
from jinja2 import Environment, FileSystemLoader, Template   
from tiddlyweb.serializations.html import Serialization as HTMLSerialization
from tiddlyweb.serializer import Serializer
from tiddlywebplugins import replace_handler

template_env = Environment(loader=FileSystemLoader('./templates/'))
BAG_OF_TEMPLATES = "templates"

def get_recipe(environ, recipe):
    store = environ['tiddlyweb.store']
    if type(recipe) in [str,unicode]:
        myRecipe = Recipe(recipe)
        myRecipe = store.get(myRecipe)
    else:
        myRecipe = Recipe('myRecipe')
        myRecipe.set_recipe(recipe)
        myRecipe.store = store
    
    return myRecipe

def get_server_prefix(environ):
    if 'server_prefix' in environ['tiddlyweb.config']:
        server_prefix = environ['tiddlyweb.config']['server_prefix']
    else:
        server_prefix = ''
    return server_prefix

def pass_through_external_serializer(environ, name, tiddlers):
    serializer = Serializer(name, environ)
    bag = Bag('tmpBag', tmpbag=True)
    bag.add_tiddlers(tiddlers)
    return serializer.list_tiddlers(bag)
    
def generate_serializer(environ, plugin_name, plugins, base_tiddlers):
    """
    recurse through the serializer stack and generate the template on the way back out.
    """
    plugin_html = {}
    logging.debug("selectors mappings are: %s\n\n" % environ['tiddlyweb.config']['selector'].mappings)
    if isinstance(plugins, dict):
        for template in plugins:
            recipe = get_recipe(environ, plugins[template])
            plugin_tiddlers = control.get_tiddlers_from_recipe(recipe)
            try:
                plugin_plugins = environ['tiddlyweb.config']['tw_pages_serializers'][template]['plugins']
                plugin_html[template] = generate_serializer(environ, template, plugin_plugins, plugin_tiddlers)
            except KeyError:
                #there is no plugin by that name, so try a separate serializer instead
                plugin_html[template] = pass_through_external_serializer(environ, template, plugin_tiddlers)
    server_prefix = get_server_prefix(environ)
    try:
        #if type(environ['tiddlyweb.config']['tw_pages_serializers'][plugin_name]['template']) == unicode:
        template = template_env.from_string(environ['tiddlyweb.config']['tw_pages_serializers'][plugin_name]['template'])
        #else:
        #    template = template_env.get_template(environ['tiddlyweb.config']['tw_pages_serializers'][plugin_name]['template'])
        content = template.render(base=base_tiddlers, extra=plugin_html, prefix=server_prefix)
    except KeyError:
        content = pass_through_external_serializer(environ, plugin_name, base_tiddlers)
    return content

def generate_index(environ, content, title, scripts, styles):
    server_prefix = get_server_prefix(environ)
    template = template_env.get_template(environ['tiddlyweb.config']['tw_pages_default']['base_template'])
    return template.render(content=content, title=title, prefix=server_prefix, scripts=scripts, styles=styles)

def get_template(environ, start_response):
    """
    generate template for main recipe
    pass sub recipes into sub serialisers and get result
    pass that result into main serialiser for inclusion
    """
    plugin_name = environ['tiddlyweb.config']['tw_pages_urls'][environ['selector.matches'][0]]['plugin_name']
    try:
        plugins = environ['tiddlyweb.config']['tw_pages_serializers'][plugin_name]['plugins']
    except KeyError:
        plugins = {}
    base_recipe = environ['tiddlyweb.config']['tw_pages_urls'][environ['selector.matches'][0]]['recipe']
    recipe = get_recipe(environ, base_recipe)
    tiddlers = control.get_tiddlers_from_recipe(recipe)
    start_response('200 OK', [
        ('Content-Type', 'text/html; charset=utf-8')
        ])
    content = generate_serializer(environ, plugin_name, plugins, tiddlers)
    try:
        page_title = environ['tiddlyweb.config']['tw_pages_urls'][environ['selector.matches'][0]]['title']
    except KeyError:
        page_title = plugin_name
    scripts = environ['tiddlyweb.config']['tw_pages_default']['scripts']
    styles = environ['tiddlyweb.config']['tw_pages_default']['styles']
    return generate_index(environ, content, page_title, scripts, styles)

class Serialization(HTMLSerialization):

    def __init__(self, environ):
        self.environ = environ
    
    def tiddler_as(self, tiddler):
        bag = Bag('tmpBag',tmpbag=True)
        bag.add_tiddler(tiddler)
        try:
            self.plugin_name = self.environ['tiddlyweb.config']['tw_pages_default']['single_tiddler']
        except IndexError:
            pass 
        self.page_title = tiddler.title
        return self.list_tiddlers(bag)

    def list_tiddlers(self, bag):
        try:
            self.plugin_name = self.environ['selector.matches'][0].rsplit('.',1)[1]
        except IndexError:
            try:
                self.plugin_name
            except AttributeError:
                self.plugin_name = self.environ['tiddlyweb.config']['tw_pages_default']['list_tiddlers']
        try:
            self.plugins = self.environ['tiddlyweb.config']['tw_pages_serializers'][self.plugin_name]['plugins']
        except KeyError:
            self.plugins = {}
        base_tiddlers = bag.list_tiddlers()
        content = generate_serializer(self.environ, self.plugin_name, self.plugins, base_tiddlers)
        try:
            self.page_title = self.environ['tiddlyweb.config']['tw_pages_serializers'][self.plugin_name]['title']
        except KeyError:
            try:
                self.page_title
            except AttributeError:
                self.page_title = self.plugin_name
        scripts = self.environ['tiddlyweb.config']['tw_pages_default']['scripts']
        styles = self.environ['tiddlyweb.config']['tw_pages_default']['styles']
        return generate_index(self.environ, content, self.page_title, scripts, styles)    

def init(config_in):
    """
    init function for tw_pages.
    Set URLs
    define serializers
    """
    config = config_in
    #set up the initial environ variables
    config['tw_pages_serializers'] = {}
    
    #get the templates out of the store
    store = Store(config['server_store'][0], {'tiddlyweb.config':config})
    bag = Bag(BAG_OF_TEMPLATES)
    bag = store.get(bag)
    tiddlers = control.get_tiddlers_from_bag(bag)
    
    for url in config['tw_pages_urls']:
        replace_handler(config['selector'], url, dict(GET=get_template))
        config['selector'].add(url, GET=get_template)        
       
#    for extension in config['tw_pages_serializers']:
#        extensionType = config['tw_pages_serializers'][extension]['type']
#        config['extension_types'][extension] = extensionType
#        config['serializers'][extensionType] = ['tw_pages','text/html; charset=UTF-8']

    for tiddler in tiddlers:
        extensionType = tiddler.type or 'text/html'
        config['extension_types'][tiddler.title] = extensionType
        config['serializers'][extensionType] = ['tw_pages','text/html; charset=UTF-8']
        logging.debug('tiddler title is qwerty: %s' % tiddler.title)
        config['tw_pages_serializers'][tiddler.title] = {
            'type': extensionType,
            'plugins': tiddler.fields,
            'template': tiddler.text
        }
