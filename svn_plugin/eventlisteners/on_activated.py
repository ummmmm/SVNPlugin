import sublime_plugin

import os.path

class SvnPluginOnActivated( sublime_plugin.EventListener ):
	def on_activated( self, view ):
		settings 	= view.settings()
		file_path	= view.file_name()

		if file_path is None or settings.has( 'SvnPluginOnActivated' ):
			return

		repository_settings = dict()
		repository_path 	= self.find_svn_folder( file_path )

		if repository_path is None:
			repository_settings[ 'is_repository' ]		= False
			repository_settings[ 'repository_path' ] 	= None
			repository_settings[ 'folder_path' ]		= None
			repository_settings[ 'file_path' ]			= None
		else:
			repository_settings[ 'is_repository' ]		= True
			repository_settings[ 'repository_path']		= repository_path
			repository_settings[ 'folder_path']			= os.path.dirname( file_path )
			repository_settings[ 'file_path' ]			= file_path

		settings.set( 'SvnPluginOnActivated', repository_settings )

	def find_svn_folder( self, path ):
		new_path = os.path.dirname( path )
		svn_path = os.path.join( new_path, '.svn' )

		if os.path.isdir( svn_path ):
			return new_path
		elif path == new_path:
			return None
		else:
			return self.find_svn_folder( new_path )
		
