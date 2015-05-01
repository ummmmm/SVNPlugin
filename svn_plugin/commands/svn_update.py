import sublime, sublime_plugin

from ..cache				import Cache
from ..utils				import in_svn_root, find_svn_root, SvnPluginCommand
from ..repository 			import Repository
from ..thread_progress 		import ThreadProgress
from ..threads.update_path 	import UpdatePathThread

class SvnPluginUpdateCommand( sublime_plugin.WindowCommand, SvnPluginCommand ):
	def run( self, path = None ):
		if path is None:
			path = find_svn_root( self.get_file() )

			if path is None:
				return

		self.repository = Repository( path )

		if not self.repository.is_tracked():
			return sublime.error_message( '{0} is not under version control' . format( path ) )

		thread = UpdatePathThread( self.repository, self.update_callback )
		thread.start()
		ThreadProgress( thread, 'Updating {0}' . format( path ), 'Updated {0}' . format( path ) )

	def update_callback( self, result ):
		if not result:
			return sublime.error_message( self.repository.svn_error )

		view = self.window.new_file()

		view.set_name( 'SVNPlugin: Update' )
		view.set_scratch( True )
		view.run_command( 'append', { 'characters': self.repository.svn_output } )
		view.set_read_only( True )

	def is_visible( self ):
		return in_svn_root( self.window.active_view().file_name() )

class SvnPluginFileUpdateCommand( SvnPluginUpdateCommand ):
	def run( self ):
		if not in_svn_root( self.get_file() ):
			return

		self.window.run_command( 'svn_plugin_update', { 'path': self.get_file() } )

	def is_visible( self ):
		return in_svn_root( self.get_file() )

class SvnPluginFolderUpdateCommand( SvnPluginUpdateCommand ):
	def run( self ):
		if not in_svn_root( self.get_folder() ):
			return

		self.window.run_command( 'svn_plugin_update', { 'path': self.get_folder() } )

	def is_visible( self ):
		return in_svn_root( self.get_folder() )
