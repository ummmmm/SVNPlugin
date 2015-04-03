import sublime, sublime_plugin

from ..cache				import Cache
from ..utils				import in_svn_root, find_svn_root, SvnPluginCommand
from ..settings 			import Settings
from ..repository 			import Repository

class SvnPluginAddCommand( sublime_plugin.WindowCommand, SvnPluginCommand ):
	def run( self, path = None ):
		if path is None:
			path = find_svn_root( self.get_file() )

			if path is None:
				return

		self.repository = Repository( path )

		if self.repository.is_tracked():
			return sublime.error_message( '{0} is already under version control' . format( path ) )

		if not self.repository.add():
			return sublime.error_message( self.repository.svn_error )

		sublime.status_message( '{0} added' . format( path ) )

class SvnPluginFileAddCommand( SvnPluginAddCommand ):
	def run( self ):
		if not in_svn_root( self.get_file() ):
			return

		self.window.run_command( 'svn_plugin_add', { 'path': self.get_file() } )

	def is_visible( self ):
		return in_svn_root( self.get_file() )

class SvnPluginFolderAddCommand( SvnPluginAddCommand ):
	def run( self ):
		if not in_svn_root( self.get_folder() ):
			return

		self.window.run_command( 'svn_plugin_add', { 'path': self.get_folder() } )

	def is_visible( self ):
		return in_svn_root( self.get_folder() )
