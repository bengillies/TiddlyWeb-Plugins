"""
TiddlyWebPages

by Ben Gillies
"""
from tiddlywebpages.url_handler import get_template

from tiddlyweb.model.bag import Bag
from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.store import NoBagError

from tiddlyweb import control
import re

BAG_OF_TEMPLATES = "templates"
BAG_OF_URLS = "urls"
DEFAULT_TEMPLATES = [
    'default',
    'application/twpages',
    'text/html'
    ]

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
            if extensionType not in DEFAULT_TEMPLATES:
                config['serializers'][extensionType] = ['tiddlywebpages.serialization','%s; charset=UTF-8' % extensionType]
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
    for mime_type in DEFAULT_TEMPLATES:
        config['serializers'][mime_type] = ['tiddlywebpages.serialization','text/html; charset=UTF-8']

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

def refresh(environ, start_response):
    """
    Provide a mechanism for somebody to update the URL list
    in selector without restarting apache. Entry point for
    selector from the url /admin/urls/refresh
    """
    start_response('200 OK', [
        ('Content-Type', 'text/html; charset=utf-8')
        ])
    register_templates(environ['tiddlyweb.config'], environ['tiddlyweb.store'])
    register_urls(environ['tiddlyweb.config'], environ['tiddlyweb.store'])
    register_config(environ['tiddlyweb.config'], environ['tiddlyweb.store'])
    return "TiddlyWebPages has been successfully updated"
