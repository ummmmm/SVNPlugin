import sublime, sublime_plugin

from ..cache				import Cache
from ..repository 			import Repository
from ..thread_progress 		import ThreadProgress
from ..threads.update_path 	import UpdatePathThread

class SvnPluginUpdateCommand( sublime_plugin.WindowCommand ):
	def run( self, path = None ):
		file_path = self.window.active_view().file_name()

		if path is None:
			if not self.is_visible():
				return

			path = Cache.cached_files[ file_path ][ 'repository' ][ 'path' ]

		self.repository = Repository( path )

		thread = UpdatePathThread( self.repository, self.update_callback )
		thread.start()
		ThreadProgress( thread, 'Updating {0}' . format( path ), 'Updated {0}' . format( path ) )

	def update_callback( self, result ):
		if not result:
			return sublime.error_message( self.repository.error )

		panel = self.window.create_output_panel( 'svn_panel' )
		self.window.run_command( 'show_panel', { 'panel': 'output.svn_panel' } )
		panel.set_read_only( False )
		panel.run_command( 'insert', { 'characters': self.repository.svn_output } )
		panel.set_read_only( True )

	def is_visible( self ):
		file_path = self.window.active_view().file_name()

		if file_path not in Cache.cached_files:
			return False

		return Cache.cached_files[ file_path ][ 'repository' ][ 'tracked' ]

class SvnPluginFileUpdateCommand( sublime_plugin.WindowCommand ):
	def run( self ):
		if not self.is_visible():
			return

		file_path = self.window.active_view().file_name()
		self.window.run_command( 'svn_plugin_update', { 'path': Cache.cached_files[ file_path ][ 'file' ][ 'path' ] } )

	def is_visible( self ):
		file_path = self.window.active_view().file_name()

		if file_path not in Cache.cached_files:
			return False

		return Cache.cached_files[ file_path ][ 'file' ][ 'tracked' ]

class SvnPluginFolderUpdateCommand( sublime_plugin.WindowCommand ):
	def run( self ):
		if not self.is_visible():
			return

		file_path = self.window.active_view().file_name()
		self.window.run_command( 'svn_plugin_update', { 'path': Cache.cached_files[ file_path ][ 'folder' ][ 'path' ] } )

	def is_visible( self ):
		file_path = self.window.active_view().file_name()

		if file_path not in Cache.cached_files:
			return False

		return Cache.cached_files[ file_path ][ 'folder' ][ 'tracked' ]	
