import sublime

class Settings():
	def __init__( self ):
		self.settings 	= None
		self.loaded		= False

	def load_settings( self ):
		if self.loaded:
			return

		self.settings 	= sublime.load_settings( 'SVNPlugin.sublime-settings' )
		self.loaded		= True

	def log_errors( self ):
		self.load_settings()

		value = self.settings.get( 'log_errors' )

		if type( value ) is not bool:
			return False

		return self.settings.get( 'log_errors' )

	def svn_log_commands( self ):
		self.load_settings()

		value = self.settings.get( 'svn_log_commands' )

		if type( value ) is not bool:
			return False

		return value

	def svn_log_panel( self ):
		self.load_settings()

		value = self.settings.get( 'svn_log_panel' )

		if type( value ) is not bool:
			return False

		return value

	def svn_log_limit( self ):
		self.load_settings()

		value = self.settings.get( 'svn_log_limit' )

		if type( value ) is not int or value < 0:
			return 100

		return value

	def svn_diff_tool( self ):
		self.load_settings()

		value = self.settings.get( 'svn_diff_tool' )

		if type( value ) is not str:
			return None

		return value

	def svn_binary( self ):
		self.load_settings()

		value = self.settings.get( 'svn_binary' )

		if type( value ) is not str:
			return None

		return value

	def svn_commit_clipboard( self ):
		self.load_settings()

		value = self.settings.get( 'svn_commit_clipboard' )

		if type( value ) is not str:
			return None

		return value
