import sublime_plugin
import os.path

from ..cache		import Cache
from ..repository 	import Repository

class SvnPluginOnActivated( sublime_plugin.EventListener ):
	def on_activated( self, view ):
		file_path = view.file_name()

		if file_path is None or file_path in Cache.cached_files:
			return

		repository_settings = dict()
		repository_path 	= self.find_svn_folder( file_path )
		folder_path 		= os.path.dirname( file_path )
		repository_tracked	= False
		folder_tracked		= False
		file_tracked		= False

		if repository_path:
			file_tracked = Repository( file_path ).is_tracked()

			if file_tracked:
				folder_tracked 		= True
				repository_tracked 	= True
			else:
				folder_tracked 		= Repository( folder_path ).is_tracked()
				repository_tracked	= True if folder_tracked else Repository( repository_path ).is_tracked()

		repository_settings[ 'repository' ] = { 'tracked': repository_tracked, 	'path': repository_path }
		repository_settings[ 'folder' ]		= { 'tracked': folder_tracked, 		'path': folder_path }
		repository_settings[ 'file' ]		= { 'tracked': file_tracked, 		'path': file_path }

		Cache.cached_files[ file_path ] = repository_settings

	def find_svn_folder( self, path ):
		new_path = os.path.dirname( path )
		svn_path = os.path.join( new_path, '.svn' )

		if os.path.isdir( svn_path ):
			return new_path
		elif path == new_path:
			return None
		else:
			return self.find_svn_folder( new_path )
		
