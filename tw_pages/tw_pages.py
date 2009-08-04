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
from jinja2 import Environment, FileSystemLoader, Template
import re

template_env = Environment(loader=FileSystemLoader('./templates/'))
BAG_OF_TEMPLATES = "templates"
BAG_OF_URLS = "urls"

RECIPE_EXTENSIONS = {}


def _extended_recipe_template(environ):
    template = {}
    try:     
        if environ:
            template['user'] = environ['tiddlyweb.usersign']['name']
    except KeyError:
        pass
    for extension in RECIPE_EXTENSIONS:
        template[extension] = RECIPE_EXTENSIONS[extension]
        
    logging.debug('zxcvb %s' % template)
    return template
        
control._recipe_template = _extended_recipe_template

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

def register_urls(config, store):
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
        logging.debug
        config['tw_pages_serializers'][tiddler.title] = {
            'title': page_title,
            'type': extensionType,
            'plugins': tiddler.fields,
            'template': tiddler.text
        }
    
def generate_serializer(environ, plugin_name, plugins, base_tiddlers):
    """
    recurse through the serializer stack and generate the template on the way back out.
    """
    plugin_html = {}
    if isinstance(plugins, dict):
        for template in plugins:
            recipe = get_recipe(environ, plugins[template])
            plugin_tiddlers = control.get_tiddlers_from_recipe(recipe)
            try:
                plugin_plugins = environ['tiddlyweb.config']['tw_pages_serializers'][template]['plugins']
                logging.debug('about to recurse with tiddlers: %s and recipe: %s' % (plugin_tiddlers,recipe))
                plugin_html[template] = generate_serializer(environ, template, plugin_plugins, plugin_tiddlers)
            except KeyError:
                #there is no plugin by that name, so try a separate serializer instead
                plugin_html[template] = pass_through_external_serializer(environ, template, plugin_tiddlers)
    server_prefix = get_server_prefix(environ)
    try:
        template = template_env.from_string(environ['tiddlyweb.config']['tw_pages_serializers'][plugin_name]['template'])
        content = template.render(base=base_tiddlers, extra=plugin_html, prefix=server_prefix)
    except KeyError:
        content = pass_through_external_serializer(environ, plugin_name, base_tiddlers)
    return content

def generate_index(environ, content, title):
    server_prefix = get_server_prefix(environ)
    template = template_env.from_string(environ['tiddlyweb.config']['tw_pages_serializers']['Default']['template'])
    return template.render(content=content, title=title, prefix=server_prefix)

def get_template(environ, start_response):
    """
    pattern match on the URL to find the correct tiddler, extract the recipe, and return the generated template
    """
    url = environ['selector.matches'][0]
    patterned = len(environ['wsgiorg.routing_args'][1]) > 0 #do we need to pattern match with the url to extract variables
    if patterned: 
        for element in environ['wsgiorg.routing_args'][1]:
            RECIPE_EXTENSIONS[element] = environ['wsgiorg.routing_args'][1][element]

    #find the correct url
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
            
    try:
        plugins = environ['tiddlyweb.config']['tw_pages_serializers'][plugin_name]['plugins']
    except KeyError:
        plugins = {}
    base_recipe = environ['tiddlyweb.config']['tw_pages_urls'][url]['recipe']
    recipe = get_recipe(environ, base_recipe)
    tiddlers = control.get_tiddlers_from_recipe(recipe)
    start_response('200 OK', [
        ('Content-Type', 'text/html; charset=utf-8')
        ])
    if plugin_name in environ['tiddlyweb.config']['tw_pages_serializers']:
        content = generate_serializer(environ, plugin_name, plugins, tiddlers)
        try:
            page_title = environ['tiddlyweb.config']['tw_pages_urls'][url]['title']
        except KeyError:
            page_title = environ['tiddlyweb.config']['tw_pages_serializers']['title'] or plugin_name
        for key, value in RECIPE_EXTENSIONS.items():
            page_title = page_title.replace('{{ ' + key + ' }}', value)
            
        content = generate_index(environ, content, page_title)
    else:
        content = pass_through_external_serializer(environ, plugin_name, tiddlers)
        
    return content


class Serialization(HTMLSerialization):

    def __init__(self, environ):
        self.environ = environ
    
    def tiddler_as(self, tiddler):
        RECIPE_EXTENSIONS['tiddler'] = tiddler.title
        RECIPE_EXTENSIONS['bag'] = tiddler.bag
        bag = Bag('tmpBag',tmpbag=True)
        bag.add_tiddler(tiddler)
        try:
            self.plugin_name = self.environ['tiddlyweb.config']['tw_pages_serializers']['Default']['plugins']['single_tiddler']
        except IndexError:
            pass 
        self.page_title = tiddler.title
        return self.list_tiddlers(bag)

    def list_tiddlers(self, bag):
        if 'bag' not in RECIPE_EXTENSIONS and not bag.tmpbag:
            RECIPE_EXTENSIONS['bag'] = bag.name
        try:
            self.plugin_name = self.environ['selector.matches'][0].rsplit('.',1)[1]
        except IndexError:
            try:
                self.plugin_name
            except AttributeError:
                self.plugin_name = self.environ['tiddlyweb.config']['tw_pages_serializers']['Default']['plugins']['list_tiddlers']
        try:
            self.plugins = self.environ['tiddlyweb.config']['tw_pages_serializers'][self.plugin_name]['plugins']
        except KeyError:
            self.plugins = {}
        base_tiddlers = bag.list_tiddlers()
        
        #get the first tiddler in the list so that we can set the title
        if type(base_tiddlers) != list:
            base_tiddlers = [t for t in base_tiddlers]
        tiddler = base_tiddlers[0]
        if tiddler.recipe:
            RECIPE_EXTENSIONS['recipe'] = tiddler.recipe
        elif 'bag' not in RECIPE_EXTENSIONS:
            RECIPE_EXTENSIONS['bag'] = tiddler.bag
        if 'tiddler' not in RECIPE_EXTENSIONS:
            RECIPE_EXTENSIONS['tiddler'] = tiddler.title
        
        if self.plugin_name in self.environ['tiddlyweb.config']['tw_pages_serializers']:
            content = generate_serializer(self.environ, self.plugin_name, self.plugins, base_tiddlers)
            self.page_title = self.environ['tiddlyweb.config']['tw_pages_serializers'][self.plugin_name]['title'] or self.plugin_name
            for key, value in RECIPE_EXTENSIONS.items():
                self.page_title = self.page_title.replace('{{ ' + key + ' }}', value)
                
            content = generate_index(self.environ, content, self.page_title)
        else:
            content = pass_through_external_serializer(self.environ, self.plugin_name, base_tiddlers)
        
        return content

def refresh_urls(environ, start_response):
    start_response('200 OK', [
        ('Content-Type', 'text/html; charset=utf-8')
        ])
    register_urls(environ['tiddlyweb.config'], environ['tiddlyweb.store'])
    return "Your urls have been successfully updated"
    
def refresh_templates(environ, start_response):
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