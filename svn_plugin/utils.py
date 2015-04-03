import os

from .cache import Cache
from .repository import Repository

def has_svn_root( path ):
	if path is None:
		return False

	if os.path.isdir( path ):
		folder = path
	else:
		folder = os.path.dirname( path )

	return True if find_svn_root( folder ) is not None else False

def find_svn_root( path ):
	if os.path.isfile( path ):
		folder = os.path.dirname( path )
	else:
		folder = path

	original_folder	= folder
	current_folder 	= folder
	last_folder		= None

	while current_folder != last_folder:
		svn_path = os.path.join( current_folder, '.svn' )

		if not os.path.isdir( svn_path ):
			last_folder 	= current_folder
			current_folder	= os.path.dirname( current_folder )
		else:
			if current_folder in Cache.folders:
				if Cache.folders[ current_folder ]:
					return current_folder
				else:
					return None

			Cache.folders[ current_folder ] = Repository( current_folder ).is_tracked()

			if Cache.folders[ current_folder ]:
				return current_folder
			else:
				return None

	Cache.folders[ original_folder ] = None

def in_svn_root( path ):
	return True if has_svn_root( path ) == True else False

class SvnPluginCommand():
	def get_folder( self, path = None ):
		if path is None:
			if hasattr( self, 'window' ):
				file_path = self.window.active_view().file_name()

				if file_path is not None:
					return os.path.dirname( file_path )
		else:
			if os.path.isfile( path ):
				return os.path.dirname( path )
			else:
				return path

		return None

	def get_file( self ):
		if hasattr( self, 'window' ):
			return self.window.active_view().file_name()

		return None
