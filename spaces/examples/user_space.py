"""
Defines an extractor that creates a public and private bag for the
user who is logged in.

This extractor is based on the cookie extractor in TiddlyWeb core
"""
from space import Space
 
from tiddlyweb.model.user import User
from tiddlyweb.model.bag import Bag
from tiddlyweb.model.recipe import Recipe
from tiddlyweb.store import NoUserError, StoreMethodNotImplemented, \
    NoBagError, NoRecipeError
from tiddlyweb.web.extractors import ExtractorInterface
from tiddlyweb.web.http import HTTP400
from tiddlyweb.util import sha

import Cookie
import logging

class Extractor(ExtractorInterface):
    """
    Look in the headers for a cookie named 'tiddlyweb_user'.
    If it is there and the secret is valid, return the
    indicated user.
    """
    def extract(self, environ, start_response):
        """
        Extract the cookie, if there, from the headers
        and attempt to validate its contents.
        """
        try:
            user_cookie = environ['HTTP_COOKIE']
            logging.debug('simple_cookie looking at cookie string: %s',
                    user_cookie)
            cookie = Cookie.SimpleCookie()
            cookie.load(user_cookie)
            cookie_value = cookie['tiddlyweb_user'].value
            secret = environ['tiddlyweb.config']['secret']
            usersign, cookie_secret = cookie_value.rsplit(':', 1)
            store = environ['tiddlyweb.store']
 
            if cookie_secret == sha('%s%s' % (usersign, secret)).hexdigest():
                user = User(usersign)
                try:
                    user = store.get(user)
                except (StoreMethodNotImplemented, NoUserError):
                    pass
                    
                #check that the user has the requisite bags
                #if they don't, create them
                public_bag = '%s_public' % user.usersign
                private_bag = '%s_private' % user.usersign
                space = {
                    'bags': {
                        public_bag: {
                            'policy': {
                                "read": [],
                                "create": [user.usersign], 
                                "manage": [user.usersign, "R:ADMIN"], 
                                "accept": [], 
                                "write": [user.usersign], 
                                "owner": user.usersign, 
                                "delete": [user.usersign, "R:ADMIN"]
                            }
                        },
                        private_bag: {
                            'policy': {
                                "read": [user.usersign],
                                "create": [user.usersign], 
                                "manage": [user.usersign, "R:ADMIN"], 
                                "accept": [], 
                                "write": [user.usersign], 
                                "owner": user.usersign, 
                                "delete": [user.usersign]
                            }
                        }
                    },
                    'recipes': {
                        '%s' % user.usersign: {
                            'recipe': [
                                ['system',''],
                                [public_bag, ''],
                                [private_bag,'']
                            ],
                            'policy': {
                                "read": [user.usersign],
                                "create": [user.usersign], 
                                "manage": [user.usersign, "R:ADMIN"], 
                                "accept": [], 
                                "write": [user.usersign], 
                                "owner": user.usersign, 
                                "delete": [user.usersign]
                            }
                        }
                    }
                }
                user_space = Space(environ) 
                user_space.create_space(space)
                    
                return {"name": user.usersign, "roles": user.list_roles()}
        except Cookie.CookieError, exc:
            raise HTTP400('malformed cookie: %s' % exc)
        except KeyError:
            pass
        return False
