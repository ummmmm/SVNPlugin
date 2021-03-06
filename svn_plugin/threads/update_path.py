import threading

class UpdatePathThread( threading.Thread ):
	def __init__( self, repository, on_complete ):
		self.repository 	= repository
		self.on_complete	= on_complete
		threading.Thread.__init__( self )

	def run( self ):
		self.on_complete( self.repository.update() )
