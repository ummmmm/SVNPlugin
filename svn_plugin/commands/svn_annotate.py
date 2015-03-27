import sublime, sublime_plugin

from ..cache					import Cache
from ..repository 				import Repository
from ..thread_progress 			import ThreadProgress
from ..threads.annotate_file	import AnnotateFileThread

class SvnPluginFileAnnotateCommand( sublime_plugin.WindowCommand ):
	def run( self, path = None, revision = None ):
		if path is None:
			path = self.window.active_view().file_name()

		if path not in Cache.cached_files or not Cache.cached_files[ path ][ 'file' ][ 'tracked' ]:
			return

		self.repository = Repository( path )

		thread = AnnotateFileThread( self.repository, revision = revision, on_complete = self.annotate_callback )
		thread.start()
		ThreadProgress( thread, 'Loading annotation', 'Annotation loaded' )

	def annotate_callback( self, result ):
		if not result:
			return sublime.error_message( self.repository.error )

		current_syntax	= self.window.active_view().settings().get( 'syntax' )
		view 			= self.window.new_file()

		view.set_name( 'SVNPlugin: Annotation' )
		view.assign_syntax( current_syntax )
		view.set_scratch( True )
		view.run_command( 'append', { 'characters': self.repository.svn_output } )
		view.set_read_only( True )

	def is_visible( self ):
		file_path = self.window.active_view().file_name()

		if file_path not in Cache.cached_files:
			return False

		return Cache.cached_files[ file_path ][ 'file' ][ 'tracked' ]
