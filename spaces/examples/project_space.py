"""
make a space as defined by PROJECT

project is defined as json so that we can customise
policies and names with a simple string replace before
creating the space.

Other options would include defining a new class that
inherits Space, and overrides some of the functions
(eg - overriding set_policy), or specifying the PROJECT
structure directly inside addproject as a dict (as with
user_space.py)
"""
from space import Space

from tiddlyweb.manage import make_command
from tiddlyweb.commands import _store

import simplejson as json

PROJECT = """{
    "bags": {
        "PROJECT_NAME_config": {
            "policy": {
                "read": [],
                "create": ["R:ADMIN"],
                "manage": ["R:ADMIN"],
                "accept": ["NONE"],
                "owner": null,
                "write": ["R:PROJECT_NAME_ADMIN", "R:ADMIN"],
                "delete": ["R:ADMIN"]
            }
        },
        "PROJECT_NAME_report": {
            "policy": {
                "read": [],
                "create": ["R:PROJECT_NAME", "R:ADMIN"],
                "manage": ["R:ADMIN"],
                "accept": ["NONE"],
                "owner": null,
                "write": ["R:PROJECT_NAME_ADMIN", "R:ADMIN"],
                "delete": ["R:ADMIN"]
            }
        },
        "PROJECT_NAME": {
            "policy": {
                "read": ["R:PROJECT_NAME", "R:ADMIN"],
                "create": ["R:PROJECT_NAME", "R:ADMIN"],
                "manage": ["R:ADMIN"],
                "accept": ["NONE"],
                "owner": null,
                "write": ["R:PROJECT_NAME", "R:ADMIN"],
                "delete": ["R:PROJECT_NAME", "R:ADMIN"]
            }
        }
    },
    "recipes": {
        "PROJECT_NAME": {
            "recipe": [
                ["system", ""],
                ["PROJECT_NAME_config", ""],
                ["PROJECT_NAME", ""]
            ],
            "policy": {
                "read": ["R:PROJECT_NAME", "R:ADMIN"],
                "create": ["R:PROJECT_NAME", "R:ADMIN"],
                "manage": ["R:ADMIN"],
                "accept": ["NONE"],
                "owner": null,
                "write": ["R:PROJECT_NAME", "R:ADMIN"],
                "delete": ["R:PROJECT_NAME", "R:ADMIN"]
            }
        },
        "PROJECT_NAME_report": {
            "recipe": [
                ["system", ""],
                ["PROJECT_NAME_config", ""],
                ["PROJECT_NAME_report", ""]
            ],
            "policy": {
                "read": [],
                "create": ["R:PROJECT_NAME", "R:ADMIN"],
                "manage": ["R:ADMIN"],
                "accept": ["NONE"],
                "owner": null,
                "write": ["R:PROJECT_NAME", "R:ADMIN"],
                "delete": ["R:PROJECT_NAME", "R:ADMIN"]
            }
        }
    }
}"""

@make_command()
def addproject(args):
    """make a project space. <project_name>"""
    if len(args) != 1:
        print >> sys.stderr, ('usage: twanager addproject <project_name>')
    
    #replace PROJECT_NAME with the actual name of the project
    this_project = PROJECT.replace('PROJECT_NAME', args[0])
    this_project = json.loads(this_project)
    
    #create the space
    project_space = Space({'tiddlyweb.store': _store()})
    project_space.create_space(this_project)

def init(config):
    pass
