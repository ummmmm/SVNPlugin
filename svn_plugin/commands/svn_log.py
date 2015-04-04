import sublime, sublime_plugin

from ..cache				import Cache
from ..settings				import Settings
from ..utils				import in_svn_root, find_svn_root, SvnPluginCommand
from ..repository 			import Repository
from ..thread_progress 		import ThreadProgress
from ..threads.log_path 	import LogPathThread

class SvnPluginLogCommand( sublime_plugin.WindowCommand, SvnPluginCommand ):
	def run( self, path = None ):
		if path is None:
			path = find_svn_root( self.get_file() )

			if path is None:
				return

		self.repository = Repository( path )

		if not self.repository.is_tracked():
			return sublime.error_message( self.repository.error )

		thread = LogPathThread( self.repository, Settings().svn_log_limit(), self.log_callback )
		thread.start()
		ThreadProgress( thread, 'Loading logs {0}' . format( path ) )

	def log_callback( self, result ):
		if not result:
			return sublime.error_message( self.repository.svn_error )

		view = self.window.new_file()

		view.set_name( 'SVNPlugin: Log' )
		view.set_scratch( True )
		view.run_command( 'append', { 'characters': self.repository.svn_output } )
		view.set_read_only( True )

	def is_visible( self ):
		return in_svn_root( self.window.active_view().file_name() )

class SvnPluginFileLogCommand( SvnPluginLogCommand ):
	def run( self ):
		if not in_svn_root( self.get_file() ):
			return

		self.window.run_command( 'svn_plugin_log', { 'path': self.get_file() } )

	def is_visible( self ):
		return in_svn_root( self.get_file() )

class SvnPluginFolderLogCommand( SvnPluginLogCommand ):
	def run( self ):
		if not in_svn_root( self.get_folder() ):
			return

		self.window.run_command( 'svn_plugin_log', { 'path': self.get_folder() } )

	def is_visible( self ):
		return in_svn_root( self.get_folder() )
