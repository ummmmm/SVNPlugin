import sublime, sublime_plugin

from ..cache					import Cache
from ..utils					import in_svn_root, SvnPluginCommand
from ..repository 				import Repository
from ..thread_progress 			import ThreadProgress
from ..threads.annotate_file	import AnnotateFileThread

class SvnPluginFileAnnotateCommand( sublime_plugin.WindowCommand, SvnPluginCommand ):
	def run( self, path = None, revision = None ):
		if path is None:
			path = self.get_file()

			if not in_svn_root( path ):
				return

		self.repository = Repository( path )

		if not self.repository.is_tracked():
			return sublime.error_message( '{0} is not under version control' . format( path ) )

		thread = AnnotateFileThread( self.repository, revision = revision, on_complete = self.annotate_callback )
		thread.start()
		ThreadProgress( thread, 'Loading annotation', 'Annotation loaded' )

	def annotate_callback( self, result ):
		if not result:
			return sublime.error_message( self.repository.svn_error )

		current_syntax	= self.window.active_view().settings().get( 'syntax' )
		view 			= self.window.new_file()

		view.set_name( 'SVNPlugin: Annotation' )
		view.assign_syntax( current_syntax )
		view.set_scratch( True )
		view.run_command( 'append', { 'characters': self.repository.svn_output } )
		view.set_read_only( True )

	def is_visible( self ):
		return in_svn_root( self.get_file() )
