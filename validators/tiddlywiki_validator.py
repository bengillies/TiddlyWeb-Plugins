"""
sanitise all tiddlywiki input by dissallowing reserved names, 
and clearing systemConfig tags.

Any tiddler in RESERVED_TITLES will be dissallowed.

Any tiddler in a named bag in tiddlywebconfig will be dissallowed

config={
    'reserved_bag_names': ['bag_name']
}
"""

from tiddlyweb.web.validator import TIDDLER_VALIDATORS, \
    InvalidTiddlerError              
from tiddlyweb.model.bag import Bag

RESERVED_TITLES = [
    'AdvancedOptions',
    'DefaultTiddlers',
    'EditTemplate',
    'MarkupPostBody',
    'MarkupPostHead',
    'MarkupPreBody',
    'MarkupPreHead',
    'OptionsPanel',
    'PageTemplate',
    'PluginManager',
    'SideBarOptions',
    'SideBarTabs',
    'TabAll',
    'TabMore',
    'TabMoreMissing',
    'TabMoreOrphans',
    'TabMoreShadowed',
    'TabTags',
    'TabTimeline',
    'ToolbarCommands',
    'ViewTemplate'
]

def check_bag(tiddler, store, bag_names):
    """
    check that the tiddler is not in the listed bags
    """
    for bag_name in bag_names:
        bag = Bag(bag_name)
        bag = store.get(bag)
        tiddlers = bag.gen_tiddlers()
        if tiddler.title in [reserved.title for reserved in tiddlers]:
            raise InvalidTiddlerError('Tiddler name is reserved: %s' \
                % tiddler.title)

def validate_tiddlywiki(tiddler, environ):
    """
    check RESERVED_TITLES, tiddlers in named bag, presence of systemConfig
    """
    if tiddler.title in RESERVED_TITLES:
        raise InvalidTiddlerError('Tiddler name is reserved: %s' \
            % tiddler.title)
    if 'systemConfig' in tiddler.tags:
        tiddler.tags.remove('systemConfig')
        
    check_bag(tiddler, environ['tiddlyweb.store'], \
        environ['tiddlyweb.config'].get('reserved_bag_names', []))
    return tiddler

def init(config_in):
    """
    init function
    """
    TIDDLER_VALIDATORS.append(validate_tiddlywiki)

