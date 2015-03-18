import sublime, sublime_plugin

from ..svn import SVN
from ..thread_progress import ThreadProgress
from ..threads.diff_path import DiffPathThread
from ..settings import Settings

NOT_SVN_DIRECTORY	= 'Directory is not a listed SVN repository'
NOT_SVN_FILE		= 'File is not in a listed SVN repository'

class SvnDiffCommand( sublime_plugin.WindowCommand ):
	def run( self, file = False, directory = False, file_path = None, directory_path = None, revision = None ):
		svn 				= SVN()
		settings			= Settings()
		path				= None
		current_file_path	= self.window.active_view().file_name()
		self.diff_tool		= settings.svn_diff_tool()

		if not svn.valid:
			return

		if file or file_path is not None:
			if file:
				path = current_file_path
			else:
				path = file_path

			if not svn.in_svn_directory( path ):
				sublime.error_message( NOT_SVN_FILE )
				return
		elif directory or directory_path is not None:
			if directory:
				path = svn.get_svn_directory( current_file_path )
			else:
				path = directory_path

			if path not in svn.directories:
				sublime.error_message( NOT_SVN_DIRECTORY )
				return
		else:
			return

		if revision is None:
			if not svn.is_modified( path ):
				sublime.message_dialog( 'No files have been modified' )
				return

		thread = DiffPathThread( svn, path, revision, self.diff_tool, self.diff_callback )
		thread.start()
		ThreadProgress( thread, 'Running diff on {0}' . format( path ) )

	def diff_callback( self, output ):
		if self.diff_tool is None:
			self.window.new_file().run_command( 'append', { 'characters': output } )
