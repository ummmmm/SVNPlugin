import sublime, sublime_plugin
import os
import re

from ..settings 	import Settings
from ..repository 	import Repository

EDITOR_EOF_PREFIX 	= '--This line, and those below, will be ignored--\n'

class SvnPluginOnPostSave( sublime_plugin.EventListener ):
	def on_post_save( self, view ):
		if not view.settings().has( 'SVNPlugin' ):
			return

		files_to_commit 	= view.settings().get( 'SVNPlugin' )
		commit_file_path	= view.file_name()
		settings			= Settings()
		clipboard_format	= settings.svn_commit_clipboard()
		repository			= Repository( files_to_commit )
		message 			= view.substr( sublime.Region( 0, view.size() ) )
		prefix_pos			= message.find( EDITOR_EOF_PREFIX )

		if prefix_pos:
			message			= message[ 0 : prefix_pos ]

		if len( message.strip() ) == 0:
			return sublime.message_dialog( 'Did not commit, log message unchanged or not specified' )

		if not repository.commit( commit_file_path ):
			return sublime.error_message( repository.svn_error )

		if clipboard_format is not None:
			commit_revision = self.find_commit_revision( repository.svn_output )

			if commit_revision is not None:
				sublime.set_clipboard( clipboard_format.replace( '$revision', commit_revision ) )

		view.settings().erase( 'SVNPlugin' )

		sublime.set_timeout( lambda: view.close(), 50 )
		sublime.set_timeout( lambda: self.delete_commit_file( commit_file_path ), 1000 )
		sublime.status_message( 'Commited file(s)' )

	def on_close( self, view ):
		if not view.settings().has( 'SVNPlugin' ):
			return

		commit_file_path = view.file_name()
		sublime.set_timeout( lambda: self.delete_commit_file( commit_file_path ), 1000 )
		sublime.status_message( "Did not commit '{0}'" . format( commit_file_path ) )

	def find_commit_revision( self, output ):
		regex 	= re.compile( 'Committed revision ([0-9]+).')
		matches	= regex.search( output )

		if not matches:
			return None

		return matches.group( 1 )

	def delete_commit_file( self, file_path ):
		if os.path.isfile( file_path ):
			try:
				os.remove( file_path )
			except:
				return False

		return True
