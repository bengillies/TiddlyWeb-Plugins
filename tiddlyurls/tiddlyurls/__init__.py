"""
TiddlyUrls

by Ben Gillies

create a friendly url that maps to a standard /recipes/foo/tiddlers or /bags/foo/tiddlers url

to use, add a tiddler to the named urls bag.
give it a title corresponding to the url you want to use (using selector syntax)
give it text corresponding to the url you want it to map to.

point your browser to "/tiddlyurls/refresh" to register/update any urls or restart your server

voila!

"""
from tiddlyurls.config import config as tiddlyurls_config
from tiddlyurls.register import register_urls, refresh_urls
from tiddlyurls.twanager import url

from tiddlyweb.config import merge_config
from tiddlyweb import control
from tiddlyweb.store import Store

def init(config):
    #merge the custom config information
    merge_config(config, tiddlyurls_config)

    #provide a way to allow people to refresh their URLs
    if 'selector' in config:
        config['selector'].add('/tiddlyurls/refresh', GET=refresh_urls)
    
        #get the store
        store = Store(config['server_store'][0], {'tiddlyweb.config':config})

        #register the urls with selector
        register_urls(store, config)

