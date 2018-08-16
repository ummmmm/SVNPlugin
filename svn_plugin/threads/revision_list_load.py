import sublime
import threading

class RevisionListLoadThread( threading.Thread ):
	def __init__( self, repository, log_limit, stop_on_copy, revision, on_complete ):
		self.repository 	= repository
		self.stop_on_copy	= stop_on_copy
		self.log_limit		= log_limit
		self.revision		= revision
		self.on_complete	= on_complete
		threading.Thread.__init__( self )

	def run( self ):
		self.on_complete( self.repository.log( self.log_limit, self.stop_on_copy, self.revision ) )
