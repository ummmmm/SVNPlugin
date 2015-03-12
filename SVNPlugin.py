class SVNPlugin():
	def __init__( self ):
		self.locked_files = set()
		self.commit_files = dict()

	def add_locked_files( self, new_set ):
		if len( self.locked_files.intersection( new_set ) ):
			return False

		self.locked_files.update( new_set )

		return True

	def add_commit_file( self, new_file, new_set ):
		self.commit_files.update( { new_file : new_set } )

	def release_locked_files( self, file ):
		for locked_file in self.commit_files[ file ]:
			self.locked_files.remove( locked_file )

		del self.commit_files[ file ]
