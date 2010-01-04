"""
binary import

import the contents at the given uri to
the given bag as a binary tiddler
"""
from tiddlyweb.model.tiddler import Tiddler
from tiddlyweb.manage import make_command
from tiddlyweb.commands import _store

import urllib
import sys

@make_command()
def bimport(args):
    """Import a tiddler as binary into a bag: <bag> <name> <URI>"""
    if len(args) != 3:
        print >> sys.stderr, ('you must specify the URI, the tiddler name ' \
            'and the bag you want to put the resulting tiddler into:\n' \
            'twanager bimport <bag> <name> <URI>')
    
    bag = args[0]
    tiddler_title = args[1]
    url = urllib.urlopen(args[2])
    
    content_type = url.headers.type
    data = url.read()
    
    tiddler = Tiddler(tiddler_title)
    tiddler.type = content_type
    tiddler.text = data
    tiddler.bag = bag
    
    _store().put(tiddler)

def init(config_in):
    global config
    config = config_in
