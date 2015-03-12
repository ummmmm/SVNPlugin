class SVNPlugin():
	def __init__( self ):
		self.locked_files = set()
		self.commit_files = dict()

	def add_locked_files( self, new_set ):
		if len( self.locked_files.intersection( new_set ) ) != 0:
			return False

		self.locked_files.update( new_set )

		return True

	def release_locked_files( self, commit_file ):
		self.locked_files = self.locked_files.difference( self.commit_files[ commit_file ] )
		del self.commit_files[ commit_file ]

	def add_commit_file( self, commit_file, new_set ):
		self.commit_files.update( { commit_file : new_set } )
