import sublime, sublime_plugin

from ..cache				import Cache
from ..settings 			import Settings
from ..repository 			import Repository

class SvnPluginAddCommand( sublime_plugin.WindowCommand ):
	def run( self, path ):
		self.repository = Repository( path )

		if not self.repository.add():
			return sublime.error_message( self.repository.error )

		sublime.status_message( '{0} added' . format( path ) )

class SvnPluginFileAddCommand( sublime_plugin.WindowCommand ):
	def run( self ):
		if not self.is_visible():
			return

		file_path = self.window.active_view().file_name()
		self.window.run_command( 'svn_plugin_add', { 'path': Cache.cached_files[ file_path ][ 'file' ][ 'path' ] } )

	def is_visible( self ):
		file_path = self.window.active_view().file_name()

		if file_path not in Cache.cached_files:
			return False

		if not Cache.cached_files[ file_path ][ 'file' ][ 'tracked' ] and Cache.cached_files[ file_path ][ 'folder' ][ 'tracked' ]:
			return True

		return False

class SvnPluginFolderAddCommand( sublime_plugin.WindowCommand ):
	def run( self ):
		if not self.is_visible():
			return

		file_path = self.window.active_view().file_name()
		self.window.run_command( 'svn_plugin_add', { 'path': Cache.cached_files[ file_path ][ 'folder' ][ 'path' ] } )

	def is_visible( self ):
		file_path = self.window.active_view().file_name()

		if file_path not in Cache.cached_files:
			return False

		if not Cache.cached_files[ file_path ][ 'folder' ][ 'tracked' ]	and Cache.cached_files[ file_path ][ 'repository' ][ 'tracked' ]:
			return True

		return False
