import sublime
import threading

class RevisionFileThread( threading.Thread ):
	def __init__( self, svn, file_path, number, on_complete ):
		self.svn 			= svn
		self.file_path		= file_path
		self.number			= number
		self.on_complete	= on_complete
		threading.Thread.__init__( self )

	def run( self ):
		content = self.svn.get_revision_content( self.file_path, self.number )

		sublime.set_timeout( lambda: self.on_complete( self.file_path, self.number, content ) )
