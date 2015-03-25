import sublime, sublime_plugin

import re
import xml.etree.ElementTree as ET
import os.path

from ..thread_progress	import ThreadProgress
from ..repository 		import Repository
from ..settings 		import Settings

EDITOR_EOF_PREFIX 	= '--This line, and those below, will be ignored--\n'

class SvnPluginCommitCommand( sublime_plugin.WindowCommand ):
	def __init__( self, window ):
		self.window 			= window
		self.settings			= Settings()
		self.commit_file_path 	= ''
		self.__error 			= ''

	def run( self, file = False, directory = False, file_path = None, directory_path = None ):
		current_file_path = self.window.active_view().file_name()

		if current_file_path is None:
			current_file_path = ''

		if file:
			path = current_file_path
		elif file_path:
			path = file_path
		elif directory:
			path = dirname( current_file_path )
		elif directory_path:
			path = directory_path
		else:
			return

		self.repository = Repository( path )

		if not self.repository.valid():
			return sublime.error_message( self.repository.error )

		if not self.repository.is_tracked():
			return sublime.error_message( self.repository.error )

		if not self.repository.status():
			return sublime.error_message( self.repository.error )

		output 	= self.repository.svn_output
		files 	= []

		try:
			root = ET.fromstring( output )
		except ET.ParseError:
			return sublime.error_message( 'Failed to parse XML' )

		try:
			for child in root.iter( 'entry' ):
				entry_path	= child.attrib[ 'path' ]
				item_status = child.find( 'wc-status' ).attrib[ 'item' ]

				if item_status == 'added' or item_status == 'modified' or item_status == 'deleted' or item_status == 'replaced':
					files.append( { 'path': entry_path, 'status': item_status[ :1 ].upper() } )

		except KeyError as e:
			return sublime.error_message( 'Failed to find key {0}' . format( str( e ) ) )

		if not files:
			return sublime.message_dialog( 'No files to commit' )

		if not self.create_commit_file( files ):
			return sublime.error_message( self.error )

		view = self.window.open_file( self.commit_file_path )
		view.settings().set( 'SVNPlugin', [ file[ 'path'] for file in files ] )

	def create_commit_file( self, files ):
		valid_path = False

		for i in range( 100 ):
			i = i if i > 0 else '' # do not append 0 to the commit file name

			file_path = os.path.join( self.repository.current_repository, 'svn-commit{0}.tmp' . format( i ) )

			if not os.path.isfile( file_path ):
				valid_path = True
				break

		if not valid_path:
			return self.log_error( 'Failed to create a unique file name' )

		try:
			with open( file_path, 'w' ) as fh:
				fh.write( '\n' )
				fh.write( EDITOR_EOF_PREFIX )
				fh.write( '\n' )

				for file in files:
					fh.write( '{0}	{1}\n' . format( file[ 'status' ], file[ 'path' ] ) )
		except Exception:
			return self.log_error( 'Failed to create commit file {0}' . format( file_path ) )

		self.commit_file_path = file_path

		return True

	def log_error( self, error ):
		self.__error = error

		if self.settings.log_errors():
			print( error )

		return False

	@property
	def error( self ):
		return self.__error
