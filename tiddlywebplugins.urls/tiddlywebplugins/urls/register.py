"""
register the urls in the named bag with selector
"""
from tiddlywebplugins.urls.handler import get_handler

from tiddlyweb.model.bag import Bag
from tiddlyweb.store import NoBagError
from tiddlyweb.control import get_tiddlers_from_bag

from selector import SimpleParser
import re
import logging

def register_urls(store, config):
    url_bag = config['url_bag']
    selector = config['selector']
    
    bag = Bag(url_bag)
    try:
        bag = store.get(bag)
    except NoBagError:
        logging.debug('tiddlywebplugins.urls Error: No bag found for urls. Please create bag \"%s\".' % url_bag)
        raise NoBagError
    
    tiddlers = get_tiddlers_from_bag(bag)
    for tiddler in tiddlers:
        register_url(selector, tiddler)

def register_url(selector, tiddler):
    replaced = False
    for index, (regex, handler) in enumerate(selector.mappings):
            if regex.match(tiddler.title) is not None or selector.parser(tiddler.title) == regex.pattern:
                handler['GET'] = get_handler
                selector.mappings[index] = (regex, handler)
                replaced = True
    if not replaced:
        selector.add(tiddler.title, GET=get_handler)

def refresh_urls(environ, start_response):
    store = environ['tiddlyweb.store']
    config = environ['tiddlyweb.config']
    
    register_urls(store, config)
    
    start_response('200 OK', [('Content-Type', 'text/html; charset=utf-8')])
    return 'All URLs have been updated'
