import sublime
import threading

class RevisionListLoadThread( threading.Thread ):
	def __init__( self, svn, settings, file_path, on_complete ):
		self.svn 			= svn
		self.settings		= settings
		self.file_path		= file_path
		self.on_complete	= on_complete
		threading.Thread.__init__( self )

	def run( self ):
		revisions = self.svn.get_revisions( self.file_path, self.settings.svn_log_limit() )

		sublime.set_timeout( lambda: self.on_complete( self.file_path, revisions ) )
