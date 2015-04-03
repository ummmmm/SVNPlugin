import sublime, sublime_plugin

from ..cache				import Cache
from ..utils				import in_svn_root, find_svn_root, SvnPluginCommand
from ..repository 			import Repository
from ..thread_progress 		import ThreadProgress
from ..threads.status_path 	import StatusPathThread

class SvnPluginStatusCommand( sublime_plugin.WindowCommand, SvnPluginCommand ):
	def run( self, path = None ):
		if path is None:
			path = find_svn_root( self.get_file() )

			if path is None:
				return

		self.repository = Repository( path )

		thread = StatusPathThread( self.repository, self.status_callback )
		thread.start()
		ThreadProgress( thread, 'Loading status', '' )

	def status_callback( self, result ):
		if not result:
			return sublime.error_message( self.repository.error )

		view = self.window.new_file()

		view.set_name( 'SVNPlugin: Status' )
		view.set_scratch( True )
		view.run_command( 'append', { 'characters': self.repository.svn_output } )
		view.set_read_only( True )

	def is_visible( self ):
		return in_svn_root( self.window.active_view().file_name() )

class SvnPluginFileStatusCommand( SvnPluginStatusCommand ):
	def run( self ):
		if not in_svn_root( self.get_file() ):
			return

		self.window.run_command( 'svn_plugin_status', { 'path': self.get_file() } )

	def is_visible( self ):
		return in_svn_root( self.get_file() )

class SvnPluginFolderStatusCommand( SvnPluginStatusCommand ):
	def run( self ):
		if not in_svn_root( self.get_folder() ):
			return

		self.window.run_command( 'svn_plugin_status', { 'path': self.get_folder() } )

	def is_visible( self ):
		return in_svn_root( self.get_folder() )
