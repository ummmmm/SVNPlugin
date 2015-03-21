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
		self.diff_tool		= settings.svn_diff_tool()

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

		repository = Repository( path )

		if not repository.valid():
			return sublime.error_message( repository.error )

		if not repository.is_tracked():
			return sublime.error_message( repository.error )

		if revision is None:
			if not repository.is_modified():
				return sublime.error_message( repository.error )

		thread = DiffPathThread( repository, revision, self.diff_tool, self.diff_callback )
		thread.start()
		ThreadProgress( thread, 'Running diff on {0}' . format( path ) )

	def diff_callback( self, output ):
		if self.diff_tool is None:
			self.window.new_file().run_command( 'append', { 'characters': output } )
