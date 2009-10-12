"""
TiddlyWebPages

by Ben Gillies
"""
from tiddlywebpages.register import refresh, register_config, \
    register_templates, register_urls, BAG_OF_URLS, BAG_OF_TEMPLATES
from tiddlywebpages.filters import JINJA_FILTERS 

from tiddlyweb.store import Store
from tiddlyweb import control

def extended_recipe_template(environ):
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

#override the recipe template behaviour to allow more dynamic recipes
control._recipe_template = extended_recipe_template

def init(config_in):
    """
    init function for tiddlywebpages.
    Set URLs
    define serializers
    """
    config = config_in
    
    #provide a way to allow people to refresh their URLs
    config['selector'].add('/admin/tiddlywebpages/refresh', GET=refresh)
                      
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
        if 'filters' in config['tw_pages']:
            for new_filter in config['tw_pages']['filters']:
                _temp = __import__(new_filter, {}, {}, [new_filter])
                JINJA_FILTERS.append((new_filter, getattr(_temp, new_filter)))
    
    register_urls(config, store)
    register_templates(config, store)
