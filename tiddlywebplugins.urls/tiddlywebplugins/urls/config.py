"""
configuration information

eg - the bag that urls belong in

todo - add a twinstance like command to auto generate a urls bag
"""

config={
    'url_bag': 'urls',
    'url_bag_description': 'This bag contains a mapping of custom URLs to ' \
        'Tiddlyweb internal URLs. NOTE - It MUST NOT contain anything else.',
    'url_bag_policy': {
        'read': [],
        'create': ['R:ADMIN'],
        'manage': ['R:ADMIN'],
        'accept': ['R:ADMIN'],
        'write': ['R:ADMIN'],
        'owner': 'administrator',
        'delete': ['R:ADMIN'],
    }
}
