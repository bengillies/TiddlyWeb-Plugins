"""
Adds a command to Twanager to easily create a url.

Takes the form:

twanager url selector_path destination
"""
from tiddlywebplugins.urls.config import config as urls_config

from tiddlyweb.manage import _store, make_command
from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.config import config

import sys

@make_command()
def url(args):
    """Add a URL via tiddlywebplugins.URLs. Redirect is optional. [--redirect] <selector_path> <destination_url>"""
    if 2 != len(args) != 3:
        print >> sys.stderr, ('you must include both the path you want to use (selector path) and the destination url')
        
    store = _store()
    
    if args[0] == '--redirect':
        redirect = args.pop(0).lstrip('-')
    else:
        redirect = None
    
    selector_path = args[0]
    destination_url = args[1]
    
    tiddler = Tiddler(selector_path)
    try:
        tiddler.bag = config['url_bag']
    except KeyError:
        tiddler.bag = urls_config['url_bag']
    
    tiddler.text = destination_url
    if redirect:
        tiddler.tags = [redirect]
    
    store.put(tiddler)
    
    return True
