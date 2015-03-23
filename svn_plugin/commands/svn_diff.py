import sublime, sublime_plugin

from os.path 				import dirname
from ..settings 			import Settings
from ..repository 			import Repository
from ..thread_progress 		import ThreadProgress
from ..threads.diff_path 	import DiffPathThread

class SvnDiffCommand( sublime_plugin.WindowCommand ):
	def run( self, file = False, directory = False, file_path = None, directory_path = None, revision = None ):
		settings 			= Settings()
		current_file_path 	= self.window.active_view().file_name()

		if current_file_path is None:
			current_file_path = ''

		if file:
			path = current_file_path
		elif file_path:
			path = file_path
		elif directory:
			path = dirname( current_file_path )
		elif directory_path:
			path = directory_path
		else:
			return

		self.repository = Repository( path )

		if not self.repository.valid():
			return sublime.error_message( self.repository.error )

		if not self.repository.is_tracked():
			return sublime.error_message( self.repository.error )

		if revision is None:
			if not self.repository.is_modified():
				return sublime.error_message( self.repository.error )

		thread = DiffPathThread( self.repository, revision, settings.svn_diff_tool(), self.diff_callback )
		thread.start()
		ThreadProgress( thread, 'Running diff on {0}' . format( path ) )

	def diff_callback( self, result ):
		if not result:
			return sublime.error_message( self.repository.error )

		if self.repository.svn_output:
			self.window.new_file().run_command( 'append', { 'characters': self.repository.svn_output } )
