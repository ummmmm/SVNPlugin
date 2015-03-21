import sublime, sublime_plugin

from os.path 				import dirname
from ..settings 			import Settings
from ..repository 			import Repository
from ..thread_progress 		import ThreadProgress
from ..threads.update_path 	import UpdatePathThread

class SvnUpdateCommand( sublime_plugin.WindowCommand ):
	def run( self, file = False, directory = False, file_path = None, directory_path = None ):
		current_file_path = self.window.active_view().file_name()

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

		thread = UpdatePathThread( repository, self.update_callback )
		thread.start()
		ThreadProgress( thread, 'Updating {0}' . format( path ), 'Updated {0}' . format( path ) )

	def update_callback( self, output ):
		panel = self.window.create_output_panel( 'svn_panel' )
		self.window.run_command( 'show_panel', { 'panel': 'output.svn_panel' } )
		panel.set_read_only( False )
		panel.run_command( 'insert', { 'characters': output } )
		panel.set_read_only( True )
