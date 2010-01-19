"""
TiddlyWebPages

by Ben Gillies
"""
from tiddlywebpages.register import refresh, register_config, \
    register_templates,  BAG_OF_TEMPLATES
from tiddlywebpages.filters import TW_PAGES_FILTERS
from tiddlywebpages.config import config as twp_config

from tiddlyweb import control
from tiddlyweb.util import merge_config

from tiddlywebplugins.utils import get_store

def init(config):
    """
    init function for tiddlywebpages.
    Set URLs
    define serializers
    """
    merge_config(config, twp_config)
    
    #provide a way to allow people to refresh their URLs
    config['selector'].add('/tiddlywebpages/refresh', GET=refresh)
                      
    #get the store
    store = get_store(config)
    
    #set the default config info
    BAG_OF_TEMPLATES = config['tw_pages']['template_bag']
    
    if 'config' in config['tw_pages']:
        register_config(config, store)
        
    for new_filter in config['tw_pages']['filters']:
        _temp = __import__(new_filter, {}, {}, [new_filter])
        TW_PAGES_FILTERS.append((new_filter, getattr(_temp, new_filter)))
        
    if 'config' in config['tw_pages']:
        register_config(config, store)
    register_templates(config, store)
    
