import sublime, sublime_plugin

from ..cache				import Cache
from ..utils				import in_svn_root, find_svn_root, SvnPluginCommand
from ..settings 			import Settings
from ..repository 			import Repository
from ..thread_progress 		import ThreadProgress
from ..threads.diff_path 	import DiffPathThread

class SvnPluginDiffCommand( sublime_plugin.WindowCommand, SvnPluginCommand ):
	def run( self, path = None, revision = None, change = None ):
		if path is None:
			path = find_svn_root( self.get_file() )

			if path is None:
				return

		self.repository = Repository( path )

		if not self.repository.is_tracked():
			return sublime.error_message( '{0} is not under version control' . format( path ) )

		if revision is None and change is None:
			if not self.repository.is_modified():
				return sublime.error_message( '{0} has not been modified' . format( path ) )

		thread = DiffPathThread( self.repository, revision, change, Settings().svn_diff_tool(), self.diff_callback )
		thread.start()
		ThreadProgress( thread, 'Running diff on {0}' . format( path ) )

	def diff_callback( self, result ):
		if not result:
			return sublime.error_message( self.repository.error )

		if self.repository.svn_output:
			self.window.new_file().run_command( 'append', { 'characters': self.repository.svn_output } )

	def is_visible( self ):
		return in_svn_root( self.window.active_view().file_name() )

class SvnPluginFileDiffCommand( SvnPluginDiffCommand ):
	def run( self, ):
		if not in_svn_root( self.get_file() ):
			return

		self.window.run_command( 'svn_plugin_diff', { 'path': self.get_file() } )

	def is_visible( self ):
		return in_svn_root( self.get_file() )
		

class SvnPluginFolderDiffCommand( SvnPluginDiffCommand ):
	def run( self ):
		if not in_svn_root( self.get_folder() ):
			return

		self.window.run_command( 'svn_plugin_diff', { 'path': self.get_folder() } )

	def is_visible( self ):
		return in_svn_root( self.get_folder() )
