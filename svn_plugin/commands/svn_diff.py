import sublime, sublime_plugin

from ..cache				import Cache
from ..settings 			import Settings
from ..repository 			import Repository
from ..thread_progress 		import ThreadProgress
from ..threads.diff_path 	import DiffPathThread

class SvnPluginDiffCommand( sublime_plugin.WindowCommand ):
	def run( self, path = None, revision = None ):
		file_path = self.window.active_view().file_name()

		if path is None:
			if not self.is_visible():
				return

			path = Cache.cached_files[ file_path ][ 'repository' ][ 'path' ]

		self.repository = Repository( path )

		if revision is None:
			if not self.repository.is_modified():
				return sublime.error_message( self.repository.error )

		thread = DiffPathThread( self.repository, revision, Settings().svn_diff_tool(), self.diff_callback )
		thread.start()
		ThreadProgress( thread, 'Running diff on {0}' . format( path ) )

	def diff_callback( self, result ):
		if not result:
			return sublime.error_message( self.repository.error )

		if self.repository.svn_output:
			self.window.new_file().run_command( 'append', { 'characters': self.repository.svn_output } )

	def is_visible( self ):
		file_path = self.window.active_view().file_name()

		if file_path not in Cache.cached_files:
			return False

		if not Cache.cached_files[ file_path ][ 'repository' ][ 'tracked' ]:
			return False

		return Repository( file_path ).is_modified()

class SvnPluginFileDiffCommand( sublime_plugin.WindowCommand ):
	def run( self ):
		if not self.is_visible():
			return

		file_path = self.window.active_view().file_name()
		self.window.run_command( 'svn_plugin_diff', { 'path': Cache.cached_files[ file_path ][ 'file' ][ 'path' ] } )

	def is_visible( self ):
		file_path = self.window.active_view().file_name()

		if file_path not in Cache.cached_files:
			return False

		if not Cache.cached_files[ file_path ][ 'file' ][ 'tracked' ]:
			return False

		return Repository( file_path ).is_modified()

class SvnPluginFolderDiffCommand( sublime_plugin.WindowCommand ):
	def run( self ):
		if not self.is_visible():
			return

		file_path = self.window.active_view().file_name()
		self.window.run_command( 'svn_plugin_diff', { 'path': Cache.cached_files[ file_path ][ 'folder' ][ 'path' ] } )

	def is_visible( self ):
		file_path = self.window.active_view().file_name()

		if file_path not in Cache.cached_files:
			return False

		if not Cache.cached_files[ file_path ][ 'folder' ][ 'tracked' ]:
			return False

		return Repository( file_path ).is_modified()
