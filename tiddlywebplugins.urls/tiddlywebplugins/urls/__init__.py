"""
TiddlyUrls

by Ben Gillies

create a friendly url that maps to a standard /recipes/foo/tiddlers or /bags/foo/tiddlers url

to use, add a tiddler to the named urls bag.
give it a title corresponding to the url you want to use (using selector syntax)
give it text corresponding to the url you want it to map to.

point your browser to "/urls/refresh" to register/update any urls or restart your server

voila!

"""
from tiddlywebplugins.urls.config import config as urls_config
from tiddlywebplugins.urls.register import register_urls, refresh_urls
from tiddlywebplugins.urls.twanager import url

from tiddlyweb.config import merge_config
from tiddlyweb import control
from tiddlyweb.store import Store

from tiddlywebplugins.utils import ensure_bag

def init(config):
    #merge the custom config information
    merge_config(config, urls_config)
    
    store = Store(config['server_store'][0], {'tiddlyweb.config':config})
    
    #make sure the urls bag exists
    bag_name = config['url_bag']
    bag_policy = config['url_bag_policy']
    bag_description = config['url_bag_description']
    
    ensure_bag(bag_name, store, bag_policy, bag_description)
    
    #provide a way to allow people to refresh their URLs
    if 'selector' in config:
        config['selector'].add('/urls/refresh', GET=refresh_urls)
        
        #register the urls with selector
        register_urls(store, config)
