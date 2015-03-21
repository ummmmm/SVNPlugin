import sublime
import threading

class DiffPathThread( threading.Thread ):
	def __init__( self, repository, revision_number, diff_tool, on_complete ):
		self.repository			= repository
		self.revision_number	= revision_number
		self.diff_tool			= diff_tool
		self.on_complete		= on_complete
		threading.Thread.__init__( self )

	def run( self ):
		if not self.repository.diff( revision_number = self.revision_number, diff_tool = self.diff_tool ):
			return sublime.error_message( self.repository.error )

		sublime.set_timeout( lambda: self.on_complete( self.repository.svn_output ) )
