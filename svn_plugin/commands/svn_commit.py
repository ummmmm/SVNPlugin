import sublime, sublime_plugin
import xml.etree.ElementTree as ET
import os
import re

from ..svn import SVN
from ..settings import Settings

NOT_SVN_DIRECTORY	= 'Directory is not a listed SVN repository'
NOT_SVN_FILE		= 'File is not in a listed SVN repository'
EDITOR_EOF_PREFIX 	= '--This line, and those below, will be ignored--\n'

class SvnCommitCommand( sublime_plugin.WindowCommand ):
	def run( self, file = False, directory = False, file_path = None, directory_path = None ):
		settings				= Settings()
		log_commands			= settings.svn_log_commands()
		log_errors				= settings.log_errors()
		svn						= SVN( log_commands = log_commands, log_errors = log_errors )
		self.commit_file_path 	= ''
		current_file_path		= self.window.active_view().file_name()

		if not svn.valid:
			return

		if file or file_path is not None:
			if file:
				path = current_file_path
			else:
				path = file_path

			if not svn.in_svn_directory( path ) or not svn.is_tracked( path ):
				sublime.error_message( NOT_SVN_FILE )
				return

			self.current_repository = svn.get_svn_directory( path )
		elif directory or directory_path is not None:
			if directory:
				path = svn.get_svn_directory( current_file_path )
			else:
				path = directory_path

			if path not in svn.directories:
				sublime.error_message( NOT_SVN_DIRECTORY )
				return

			self.current_repository = path
		else:
			return

		xml 	= svn.status( path )
		files 	= set()

		if xml is None:
			return

		try:
			root = ET.fromstring( xml )
		except ET.ParseError:
			self.log_error( 'Failed to parse XML' )
			return

		try:
			for child in root.iter( 'entry' ):
				entry_path	= child.attrib[ 'path' ]
				item_status = child.find( 'wc-status' ).attrib[ 'item' ]

				if item_status == 'added' or item_status == 'modified' or item_status == 'deleted' or item_status == 'replaced':
					files.add( entry_path )

		except KeyError as e:
			self.log_error( 'Failed to find key {0}' . format( str( e ) ) )
			return

		if len( files ) == 0:
			return sublime.message_dialog( 'No files to commit' )

		content = svn.status( path, xml = False, quiet = True ).strip()

		if not self.create_commit_file( content ):
			return sublime.error_message( 'Failed to create commit file' )

		view = self.window.open_file( '{0}:0:0' . format( self.commit_file_path ), sublime.ENCODED_POSITION )
		view.settings().set( 'SVNPlugin', list( files ) )

	def create_commit_file( self, message ):
		valid_path = False

		for i in range( 100 ):
			i = i if i > 0 else '' # do not append 0 to the commit file name

			file_path = os.path.join( self.current_repository, 'svn-commit{0}.tmp' . format( i ) )

			if not os.path.isfile( file_path ):
				valid_path = True
				break

		if not valid_path:
			self.self.log_error( 'Failed to create a unique file name' )
			return False

		try:
			with open( file_path, 'w' ) as fh:
				fh.write( '\n' )
				fh.write( EDITOR_EOF_PREFIX )
				fh.write( '\n' )
				fh.write( message )
		except Exception as e:
			self.log_error( "Failed to create commit file '{0}'" . format( file_path ) )
			return False

		self.commit_file_path = file_path

		return True

	def log_error( self, error ):
		if self.settings.log_errors():
			print( error )

class SvnCommitSave( sublime_plugin.EventListener ):
	def on_post_save( self, view ):
		if not view.settings().has( 'SVNPlugin' ):
			return

		files_to_commit = view.settings().get( 'SVNPlugin' )

		if len( files_to_commit ) == 0:
			return sublime.error_message( 'No files to commit' )


		file_path 			= view.file_name()
		settings			= Settings()
		svn					= SVN()
		clipboard_format	= settings.svn_commit_clipboard()

		if not svn.valid:
			return

		message 	= view.substr( sublime.Region( 0, view.size() ) )
		prefix_pos	= message.find( EDITOR_EOF_PREFIX )

		if prefix_pos:
			message	= message[ 0 : prefix_pos ]

		if len( message.strip() ) == 0:
			return sublime.message_dialog( 'Did not commit, log message unchanged or not specified' )

		result, output = svn.commit_file( file_path, files_to_commit )

		if not result:
			return sublime.error_message( 'Failed to commit file(s)' )


		if clipboard_format is not None:
			commit_revision = self.find_commit_revision( output )

			if commit_revision is not None:
				sublime.set_clipboard( clipboard_format.replace( '$revision', commit_revision ) )

		view.settings().erase( 'SVNPlugin' )

		sublime.set_timeout( lambda: view.close(), 50 )
		sublime.set_timeout( lambda: self.delete_commit_file( file_path ), 1000 )
		sublime.status_message( 'Commited file(s)' )

	def on_close( self, view ):
		if not view.settings().has( 'SVNPlugin' ):
			return

		file_path1 = view.file_name()
		sublime.set_timeout( lambda: self.delete_commit_file( file_path1 ), 1000 )
		sublime.status_message( "Did not commit '{0}'" . format( view.file_name() ) )

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
