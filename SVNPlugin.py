import sys
import imp
import os.path

reloader_name = 'SVNPlugin.svn_plugin.reloader'

if reloader_name in sys.modules:
	imp.reload( sys.modules[ reloader_name ] )

from .svn_plugin.commands import *
from .svn_plugin.reloader import *
