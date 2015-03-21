import sublime
import threading

class UpdatePathThread( threading.Thread ):
	def __init__( self, repository, on_complete ):
		self.repository 	= repository
		self.on_complete	= on_complete
		threading.Thread.__init__( self )

	def run( self ):
		if not self.repository.update():
			return sublime.error_message( self.repository.error )

		sublime.set_timeout( lambda: self.on_complete( self.repository.svn_output ) )
