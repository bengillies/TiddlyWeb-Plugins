"""
Adds a command to Twanage to easily create a url.

Takes the form:

twanager url selector_path destination
"""
from tiddlyurls.config import config as tiddlyurls_config

from tiddlyweb.manage import _store, make_command
from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.model.bag import Bag
from tiddlyweb.store import NoBagError
from tiddlyweb.config import config

@make_command()
def url(args):
    """Add a URL via TiddlyURLs. <selector_path> <destination_url>"""
    if len(args) != 2:
        print >> sys.stderr, ('you must include both the path you want to use (selector path) and the destination url')
        
    store = _store()
    
    selector_path = args[0]
    destination_url = args[1]
    
    tiddler = Tiddler(selector_path)
    try:
        tiddler.bag = config['url_bag']
    except KeyError:
        tiddler.bag = tiddlyurls_config['url_bag']
    tiddler.text = destination_url
    
    store.put(tiddler)
    
    return True
