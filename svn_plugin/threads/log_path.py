import threading

class LogPathThread( threading.Thread ):
	def __init__( self, repository, limit, on_complete ):
		self.repository 	= repository
		self.limit			= limit
		self.on_complete	= on_complete
		threading.Thread.__init__( self )

	def run( self ):
		self.on_complete( self.repository.log( xml = False, limit = self.limit ) )
