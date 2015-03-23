import sublime
import threading

class RevisionFileThread( threading.Thread ):
	def __init__( self, repository, revision, on_complete ):
		self.repository 	= repository
		self.revision		= revision
		self.on_complete	= on_complete
		threading.Thread.__init__( self )

	def run( self ):
		self.on_complete( self.repository.cat( revision = self.revision ) )
