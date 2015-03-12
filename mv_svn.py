import sublime, sublime_plugin
import os
import shlex
import subprocess
import xml.etree.ElementTree as ET
from .SVNPlugin import SVNPlugin

svn_plugin			= SVNPlugin()
tmp_commits			= dict()
EDITOR_EOF_PREFIX 	= '--This line, and those below, will be ignored--\n'
NOT_SVN_FILE		= 'File is not in a listed SVN repository'
NOT_SVN_DIRECTORY	= 'Directory is not a listed SVN repository'

#
# SVN Commit Related
#

class SvnCommitCommand( sublime_plugin.WindowCommand ):
	def run( self, file = False, directory = False, file_path = None, directory_path = None ):
		svn						= SVN()
		self.commit_file_path 	= ''
		current_file_path		= self.window.active_view().file_name()

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

		if not svn_plugin.add_locked_files( files ):
			return sublime.error_message( 'One or more files are currently locked' )

		content = svn.status( path, xml = False, quiet = True ).strip()

		if not self.create_commit_file( content ):
			return sublime.error_message( 'Failed to create commit file' )

		svn_plugin.add_commit_file( self.commit_file_path, files )

		self.window.open_file( '{0}:0:0' . format( self.commit_file_path ), sublime.ENCODED_POSITION )

	def create_commit_file( self, message ):
		valid_path = False

		for i in range( 100 ):
			i = i if i > 0 else '' # do not append 0 to the commit file name

			file_path = os.path.join( self.current_repository, 'svn-commit{0}.tmp' . format( i ) )

			if not os.path.isfile( file_path ):
				valid_path = True
				break

		if not valid_path:
			self.svn.log_error( 'Failed to create a unique file name' )
			return False

		try:
			with open( file_path, 'w' ) as fh:
				fh.write( '\n' )
				fh.write( EDITOR_EOF_PREFIX )
				fh.write( '\n' )
				fh.write( message )
		except Exception:
			self.log_error( "Failed to create commit file '{0}'" . format( file_path ) )
			return False

		self.commit_file_path = file_path

		return True

	def log_error( self, error ):
		print( error )

class SvnCommitSave( sublime_plugin.EventListener ):
	def on_post_save( self, view ):
		file_path = view.file_name()

		if file_path not in svn_plugin.commit_files:
			return

		svn					= SVN()
		files_to_commit		= svn_plugin.commit_files[ file_path ]

		if len( files_to_commit ) == 0:
			return sublime.message_dialog( 'No files to commit' )

		message 	= view.substr( sublime.Region( 0, view.size() ) )
		prefix_pos	= message.find( EDITOR_EOF_PREFIX )

		if prefix_pos:
			message	= message[ 0 : prefix_pos ]

		if len( message.strip() ) == 0:
			return sublime.message_dialog( 'Did not commit, log message unchanged or not specified' )

		if not svn.commit_file( file_path, files_to_commit ):
			return sublime.error_message( 'Failed to commit file(s)' )

		sublime.status_message( 'Commited file(s)' )
		svn_plugin.release_locked_files( file_path )
		self.delete_commit_file( file_path )
		view.close()

	def on_close( self, view ):
		file_path = view.file_name()

		if file_path not in svn_plugin.commit_files:
			return

		svn_plugin.release_locked_files( file_path )
		self.delete_commit_file( file_path )
		sublime.status_message( "Did not commit '{0}'" . format( view.file_name() ) )

	def delete_commit_file( self, file_path ):
		if os.path.isfile( file_path ):
			try:
				os.remove( file_path )
			except:
				return False

		return True

#
# SVN Info Related
#

class SvnInfoCommand( sublime_plugin.WindowCommand ):
	def run( self, file = False, directory = False ):
		if ( file == directory ):
			return

		self.svn					= SVN()
		self.file_path				= self.window.active_view().file_name()
		self.commit_panel			= None
		self.validate_file_paths	= set()

		if directory:
			return self.info_directory_quick_panel()

		return self.info_file_quick_panel( self.file_path )


	def info_directory_quick_panel( self ):
		self.show_quick_panel( self.svn.directories, self.info_directory_callback )

	def info_directory_callback( self, index ):
		if index == -1:
			return

		directory = self.svn.directories[ index ]

		directory_entries = [ { 'code': 'up', 'value': '..' }, { 'code': 'vf', 'value': 'View Files' }, { 'code': 'vr', 'value': 'View Revisions' } ]

		if self.svn.is_modified( directory ):
			directory_entries.insert( 2, { 'code': 'mf', 'value': 'View Modified Files' } )

		self.show_quick_panel( [ entry[ 'value' ] for entry in directory_entries ], lambda index: self.directory_action_callback( directory_entries, index ) )

	def directory_action_callback( self, directory_entries, index ):
		if index == -1:
			return
		elif index == 0:
			return self.info_directory_quick_panel()


	def info_file_quick_panel( self, file_path ):
		if file_path not in self.validate_file_paths:
			if not self.svn.in_svn_directory( self.file_path ):
				sublime.error_message( NOT_SVN_FILE )
				return

			self.validate_file_paths.add( file_path )

		if not self.svn.is_tracked( file_path ):
			top_level_file_entries = [ { 'code': 'af', 'value': 'Add File to Repository' } ]
		else:
			top_level_file_entries = [ { 'code': 'vr', 'value': 'Revisions' } ]

			if self.svn.is_modified( file_path ):
				top_level_file_entries.extend( [ { 'code': 'cf', 'value': 'Commit' }, { 'code': 'rf', 'value': 'Revert' }, { 'code': 'df', 'value': 'Diff' } ] )

		self.show_quick_panel( [ entry[ 'value' ] for entry in top_level_file_entries ], lambda index: self.info_file_callback( file_path, top_level_file_entries, index ) )

	def info_file_callback( self, file_path, entries, index ):
		if index == -1:
			return

		offset	= 0
		code 	= entries[ index - offset ][ 'code' ]

		if code == 'af':
			return self.svn.add_file( file_path )
		elif code == 'vr':
			return self.revisions_quick_panel( file_path )
		elif code == 'cf':
			return self.window.run_command( 'svn_commit', { 'file_path': file_path } )
		elif code == 'rf':
			return self.svn.revert_file( file_path )
		elif code == 'df':
			return self.window.run_command( 'svn_diff', { 'file_path': file_path } )


	def revisions_quick_panel( self, file_path ):
		revisions 			= self.svn.get_revisions( file_path, self.svn.settings.get( 'svn_log_limit', 100 ) )
		revisions_formatted = [ [ '..' ] ]

		for revision in revisions:
			revisions_formatted.extend( [ self.revision_format( revision ) ] )

		self.show_quick_panel( revisions_formatted, lambda index: self.revision_callback( file_path, revisions, index ), lambda index: self.revision_highlight( revisions, index  ) )

	def revision_callback( self, file_path, revisions, index ):
		self.hide_panel()

		if index == -1:
			return
		elif index == 0:
			return self.info_file_quick_panel( file_path )

		offset				= 1
		revision_index 		= index - offset
		entries 			= [ { 'code': 'up', 'value': '..' }, { 'code': 'vf', 'value': 'View' }, { 'code': 'af', 'value': 'Annotate' } ]

		if revision_index != 0 or self.svn.is_modified( file_path ): # only show diff option if the current revision has been modified locally or it's an older revision
			entries.insert( 2, { 'code': 'df', 'value': 'Diff' } )

		self.show_quick_panel( [ entry[ 'value' ] for entry in entries ], lambda index: self.revision_action_callback( file_path, entries, revisions, revision_index, index ) )

	def revision_action_callback( self, file_path, entries, revisions, revision_index, index ):
		if index == -1:
			return

		code = entries[ index ][ 'code' ]

		if code == 'up':
			return self.revisions_quick_panel( file_path )

		revision = revisions[ revision_index ]

		if code == 'vf':
			return self.view_revision( revision[ 'path' ], revision[ 'number' ] )
		elif code == 'df':
			return self.diff_revision( revision[ 'path' ], revision[ 'number' ] )
		elif code == 'af':
			return self.annotate_revision( revision[ 'path' ], revision[ 'number' ] )

	def revision_highlight( self, revisions, index ):
		if index == -1:
			return
		elif index == 0:
			return self.show_panel( None )

		offset 		= 1
		revision	= revisions[ index - offset ]

		self.show_panel( revision[ 'message' ] )

	def revision_format( self, revision ):
		return 'r{0} | {1} | {2}' . format( revision[ 'number' ], revision[ 'author' ], revision[ 'date' ] )


	def diff_revision( self, file_path, number ):
		self.window.run_command( 'svn_diff', { 'file_path' : file_path, 'revision' : number } )

	def annotate_revision( self, file_path, number ):
		content 		= self.svn.annotate( file_path, number )
		current_syntax	= self.window.active_view().settings().get( 'syntax' )
		view			= self.window.new_file()

		view.run_command( 'append', { 'characters': content } )
		view.set_syntax_file( current_syntax )

	def view_revision( self, file_path, number ):
		content			= self.svn.get_revision_content( file_path, number )
		current_syntax 	= self.window.active_view().settings().get( 'syntax' )
		view 			= self.window.new_file()

		view.run_command( 'append', { 'characters': content } )
		view.set_syntax_file( current_syntax )


	def show_quick_panel( self, entries, on_select, on_highlight = None ):
		sublime.set_timeout( lambda: self.window.show_quick_panel( entries, on_select, on_highlight = on_highlight ), 10 )

	def show_panel( self, content ):
		if self.svn.settings.get( 'show_panel', True ):
			self.commit_panel = self.window.create_output_panel( 'svn_panel' )
			self.window.run_command( 'show_panel', { 'panel': 'output.svn_panel' } )
			self.commit_panel.set_read_only( False )
			self.commit_panel.run_command( 'append', { 'characters': content } )
			self.commit_panel.set_read_only( True )

	def hide_panel( self ):
		if self.commit_panel:
				self.window.run_command( 'hide_panel', { 'panel': 'output.svn_panel' } )
				self.commit_panel = None

#
# SVN Diff Related
#

class SvnDiffCommand( sublime_plugin.WindowCommand ):
	def run( self, file = False, directory = False, file_path = None, directory_path = None, revision = None ):
		svn 				= SVN()
		path				= None
		current_file_path	= self.window.active_view().file_name()
		diff_tool 			= svn.settings.get( 'svn_diff_tool', None )

		if file or file_path is not None:
			if file:
				path = current_file_path
			else:
				path = file_path

			if not svn.in_svn_directory( path ):
				sublime.error_message( NOT_SVN_FILE )
				return
		elif directory or directory_path is not None:
			if directory:
				path = svn.get_svn_directory( current_file_path )
			else:
				path = directory_path

			if path not in svn.directories:
				sublime.error_message( NOT_SVN_DIRECTORY )
				return
		else:
			return

		if revision is None:
			if not svn.is_modified( path ):
				sublime.message_dialog( 'No files have been modified' )
				return

		output = svn.diff( path, revision, diff_tool )

		if diff_tool is None:
			self.window.new_file().run_command( 'append', { 'characters': output } )

#
# SVN Update Related
#

class SvnUpdateCommand( sublime_plugin.WindowCommand ):
	def run( self, file = False, directory = False, file_path = None, directory_path = None ):
		svn 				= SVN()
		path				= None
		current_file_path	= self.window.active_view().file_name()

		if file or file_path is not None:
			if file:
				path = current_file_path
			else:
				path = file_path

			if not svn.in_svn_directory( path ):
				sublime.error_message( NOT_SVN_FILE )
				return
		elif directory or directory_path is not None:
			if directory:
				path = svn.get_svn_directory( current_file_path )
			else:
				path = directory_path

			if path not in svn.directories:
				sublime.error_message( NOT_SVN_DIRECTORY )
				return
		else:
			return

		panel = self.window.create_output_panel( 'svn_panel' )
		self.window.run_command( 'show_panel', { 'panel': 'output.svn_panel' } )
		panel.set_read_only( False )
		panel.run_command( 'insert', { 'characters': svn.update( path ) } )
		panel.set_read_only( True )

#
# Helper Classes
#

class SVN():
	def __init__( self ):
		self.settings 			= sublime.load_settings( 'mv_svn.sublime-settings' )
		self.svn_binary			= self.settings.get( 'svn', None )
		self.cached_revisions	= dict()
		self.cached_path_info	= dict()
		self.directories		= self.valid_directories()

		if self.svn_binary is None:
			sublime.error_message( 'An SVN binary program needs to be set in user settings!' )
			return
		elif not os.access( self.svn_binary, os.X_OK ):
			sublime.error_message( 'The SVN binary needs to be executable!' )
			return

	def valid_directories( self ):
		directories 			= set()
		settings_directories	= self.settings.get( 'svn_directories', [] )

		if type( settings_directories ) is not list:
			self.log_error( 'Invalid SVN directory type' )
			return []

		for directory in settings_directories:
			normpath = os.path.normpath( directory )

			if self.is_tracked( normpath ):
				directories.add( normpath )

		return list( directories )

	def get_revisions( self, path, limit = None ):
		if path in self.cached_revisions:
			return self.cached_revisions[ path ]

		revisions = []

		if limit is None:
			command = 'log --xml {0}' . format( shlex.quote( path ) )
		else:
			command = 'log --xml --limit={0} {1}' . format( limit, shlex.quote( path ) )

		returncode, output, error  = self.run_command( command )

		if returncode != 0:
			self.log_error( error )
			return []

		try:
			root = ET.fromstring( output )
		except ET.ParseError:
			self.log_error( 'Failed to parse XML - {0}' . format( output ) )
			return []

		for child in root.iter( 'logentry' ):
			revisions.append( { 'path': path, 'number': child.attrib['revision'], 'author': child[ 0 ].text, 'date': child[ 1 ].text, 'message': child[ 2 ].text.strip() } )

		self.cached_revisions[ path ] = revisions

		return revisions

	def get_revision_content( self, file_path, revision ):
		returncode, output, error = self.run_command( 'cat -r{0} {1}' . format( revision, shlex.quote( file_path ) ) )

		if returncode != 0:
			self.log_error( error )
			return ''

		return output

	def get_status( self, path, quiet = True, xml = False ):
		command = 'status'

		if quiet:
			command += ' --quiet'

		if xml:
			command += ' --xml'

		command += ' {0}' . format( shlex.quote( path ) )

		returncode, output, error = self.run_command( command )

		if returncode != 0:
			svn.log_error( error )
			return ''

		return output


	def is_tracked( self, file_path ):
		if file_path in self.cached_path_info:
			return self.cached_path_info[ file_path ][ 'is_tracked' ]

		result						= False
		returncode, output, error 	= self.run_command( 'info --xml {0}' . format( shlex.quote( file_path ) ) )

		if returncode != 0:
			self.log_error( error )
			return False

		try:
			root = ET.fromstring( output )
		except ET.ParseError:
			self.log_error( 'Failed to parse XML' )
			return False

		for child in root.iter( 'entry' ):
			try:
				if file_path == child.attrib[ 'path' ]:
					result = True
					break

			except KeyError:
				self.log_error( 'Failed to find path attribute' )

		self.cached_path_info.update( { 'is_tracked': result } )

		return result

	def is_modified( self, path ):
		if path in self.cached_path_info:
			return self.cached_path_info[ path ][ 'is_modified' ]

		result						= False
		returncode, output, error 	= self.run_command( 'status --xml {0}' . format( shlex.quote( path ) ) )

		if returncode != 0:
			self.log_error( error )
			return False

		try:
			root = ET.fromstring( output )
		except ET.ParseError:
			self.log_error( 'Failed to parse XML' )
			return False

		for child in root.iter( 'entry' ):
			for wc_status in child.getiterator( 'wc-status' ):
				value = wc_status.get( 'item', 'none' )

				if value == 'added' or value == 'deleted' or value == 'replaced' or value == 'modified' or value == 'merged' or value == 'conflicted':
					result = True
					break

		self.cached_path_info.update( { 'is_modified': result } )

		return result

	def add_file( self, file_path ):
		returncode, output, error = self.run_command( 'add {0}' . format( shlex.quote( file_path ) ) )

		if returncode != 0:
			self.log_error( error )
			return False

		return True

	def revert_file( self, file_path ):
		if not sublime.ok_cancel_dialog( 'Are you sure you want to revert file:\n\n{0}' . format( file_path ), 'Yes, revert' ):
			sublime.status_message( 'File not reverted' )
			return

		returncode, output, error = self.run_command( 'revert {0}' . format( shlex.quote( file_path ) ) )

		if returncode != 0:
			self.log_error( error )
			sublime.error_message( 'Failed to revert file' )

		sublime.status_message( 'Reverted file' )

	def commit_file( self, commit_file_path, paths ):
		if not os.path.isfile( commit_file_path ):
			self.log_error( "Failed to find commit file '{0}'" . format( commit_file_path ) )
			return False

		files_to_commit = '' # passed in paths will be a set of 1 or more items

		for path in paths:
			files_to_commit += shlex.quote( path )

		returncode, output, error = self.run_command( 'commit --file={0} {1}' . format( commit_file_path, files_to_commit ) )

		if returncode != 0:
			self.log_error( error )
			return False

		return True

	def annotate( self, file_path, revision ):
		returncode, output, error = self.run_command( 'annotate --revision={0} {1}' . format( revision, shlex.quote( file_path ) ) )

		if returncode != 0:
			self.log_error( error )
			return ''

		return output

	def diff( self, path, revision = None, diff_tool = None ):
		command		= ''

		if revision:
			command += '--revision={0}' . format( revision )

		if diff_tool is not None:
			command += ' diff --diff-cmd={0} {1}' . format( diff_tool, shlex.quote( path ) )
			self.run_command( command, in_background = True )
			return ''

		command 		+= ' diff {0}' . format( shlex.quote( path ) )
		returncode, output, error = self.run_command( command )

		if returncode != 0:
			self.log_error( error )
			return ''

		return output

	def update( self, path ):
		returncode, output, error = self.run_command( 'update {0}' . format( shlex.quote( path ) ) )

		if returncode != 0:
			self.log_error( error )
			return ''

		return output

	def status( self, path, xml = True, quiet = False ):
		command = 'status'

		if xml:
			command += ' --xml'
		elif quiet:
			command += ' --quiet'

		command += ' {0}' . format( shlex.quote( path ) )

		returncode, output, error = self.run_command( command )

		if returncode != 0:
			self.log_error( error )
			return None

		return output

	def run_command( self, command, in_background = False ):
		command = '{0} {1}' . format( self.svn_binary, command )

		if self.settings.get( 'svn_log_commands', False ):
			print( command )

		if in_background:
			subprocess.Popen( command, shell = True, cwd = '/tmp' )
		else:
			process			= subprocess.Popen( command, stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell = True, cwd = '/tmp' )
			stdout, stderr	= process.communicate()
			stdout 			= stdout.decode()
			stderr 			= stderr.decode()
			return process.returncode, stdout, stderr

		return None

	def in_svn_directory( self, file_path ):
		if file_path is None:
			return False

		for directory in self.directories:
			dir_length = len( directory )

			if file_path.startswith( directory ) and file_path[ dir_length : dir_length + 1 ] == os.sep:
				return True

		return False

	def get_svn_directory( self, file_path ):
		if file_path is None:
			return None

		for directory in self.directories:
			dir_length = len( directory )

			if file_path.startswith( directory ) and file_path[ dir_length : dir_length + 1 ] == os.sep:
				return directory

		return None

	def log_error( self, error ):
		if self.settings.get( 'svn_log_errors', False ):
			print( error )

#
# Helper Functions
#
