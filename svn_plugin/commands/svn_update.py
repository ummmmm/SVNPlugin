import sublime, sublime_plugin

from os.path 				import dirname
from ..settings 			import Settings
from ..repository 			import Repository
from ..thread_progress 		import ThreadProgress
from ..threads.update_path 	import UpdatePathThread

class SvnUpdateCommand( sublime_plugin.WindowCommand ):
	def run( self, file = False, directory = False, file_path = None, directory_path = None ):
		current_file_path = self.window.active_view().file_name()

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
