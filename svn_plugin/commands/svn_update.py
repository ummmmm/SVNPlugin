import sublime, sublime_plugin

from ..svn import SVN
from ..thread_progress import ThreadProgress
from ..threads.update_path import UpdatePathThread

NOT_SVN_DIRECTORY	= 'Directory is not a listed SVN repository'
NOT_SVN_FILE		= 'File is not in a listed SVN repository'

class SvnUpdateCommand( sublime_plugin.WindowCommand ):
	def run( self, file = False, directory = False, file_path = None, directory_path = None ):
		svn 				= SVN()
		path				= None
		current_file_path	= self.window.active_view().file_name()

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

		thread = UpdatePathThread( svn, path, self.update_callback )
		thread.start()
		ThreadProgress( thread, 'Updating {0}' . format( path ), 'Updated {0}' . format( path ) )

	def update_callback( self, output ):
		panel = self.window.create_output_panel( 'svn_panel' )
		self.window.run_command( 'show_panel', { 'panel': 'output.svn_panel' } )
		panel.set_read_only( False )
		panel.run_command( 'insert', { 'characters': output } )
		panel.set_read_only( True )
