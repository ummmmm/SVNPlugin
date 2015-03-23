import sublime
import threading

class RevisionListLoadThread( threading.Thread ):
	def __init__( self, repository, log_limit, revision, on_complete ):
		self.repository 	= repository
		self.log_limit		= log_limit
		self.revision		= revision
		self.on_complete	= on_complete
		threading.Thread.__init__( self )

	def run( self ):
		self.on_complete( self.repository.log( self.log_limit, self.revision ) )
