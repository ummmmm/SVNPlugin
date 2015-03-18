import sublime
import threading

class DiffPathThread( threading.Thread ):
	def __init__( self, svn, path, number, diff_tool, on_complete ):
		self.svn 			= svn
		self.path			= path
		self.number			= number
		self.diff_tool		= diff_tool
		self.on_complete	= on_complete
		threading.Thread.__init__( self )

	def run( self ):
		output = self.svn.diff( self.path, self.number, self.diff_tool )

		sublime.set_timeout( lambda: self.on_complete( output ) )
