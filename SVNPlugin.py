import sys
import imp
import sublime

reloader_name = 'SVNPlugin.svn_plugin.reloader'

if reloader_name in sys.modules:
	imp.reload( sys.modules[ reloader_name ] )

from .svn_plugin.commands 		import *
from .svn_plugin.eventlisteners import *
from .svn_plugin.reloader 		import *
from .svn_plugin.svn 			import SVN

def plugin_loaded():
	settings = sublime.load_settings( 'SVNPlugin.sublime-settings' )

	try:
		SVN.init( binary = settings.get( 'svn_binary', None ), log_commands = settings.get( 'svn_log_commands', False ) )
	except Exception as e:
		sublime.error_message( str( e ) )
