import sublime
import threading

class UpdatePathThread( threading.Thread ):
	def __init__( self, svn, path, on_complete ):
		self.svn 			= svn
		self.path			= path
		self.on_complete	= on_complete
		threading.Thread.__init__( self )

	def run( self ):
		output = self.svn.update( self.path )

		sublime.set_timeout( lambda: self.on_complete( output ) )
