import sublime

# Credit goes to https://github.com/wbond/package_control/blob/master/package_control/thread_progress.py

class ThreadProgress():
	def __init__( self, thread, message, success_message = '' ):
		self.thread 			= thread
		self.message 			= message
		self.success_message 	= success_message
		self.addend 			= 1
		self.size 				= 8

		sublime.set_timeout( lambda: self.run( 0 ), 100 )

	def run( self, i ):
		if not self.thread.is_alive():
			if hasattr( self.thread, 'result' ) and not self.thread.result:
				return sublime.status_message('')

			return sublime.status_message( self.success_message )

		before 	= i % self.size
		after 	= ( self.size - 1 ) - before

		sublime.status_message( '{0} [{1}={2}]' . format( self.message, ' ' * before, ' ' * after ) )

		if not after:
			self.addend = -1

		if not before:
			self.addend = 1

		i += self.addend

		sublime.set_timeout( lambda: self.run( i ), 100 )
