import sublime, sublime_plugin
import os
import re
import shlex
import subprocess
import xml.etree.ElementTree as ET

tmp_commits			= dict()
EDITOR_EOF_PREFIX 	= '--This line, and those below, will be ignored--\n'

#
# SVN Commit Related
#

class SvnCommitCommand( sublime_plugin.WindowCommand ):
	def run( self, file = False, directory = False, project = False ):
		self.svn				= SVN( self.window )
		self.commit_file_path 	= ''

		if not self.svn.valid or ( file == False and directory == False and project == False ):
			return

		if file:
			if self.svn.file_tracked:
				path = self.svn.current_file
			else:
				sublime.error_message( 'File is not under version control' )
				return
		elif directory:
			if self.svn.directory_tracked:
				path = self.svn.current_directory
			else:
				sublime.error_message( 'Directory is not under version control' )
				return
		elif project:
			if self.svn.project_tracked:
				path = self.svn.current_project
			else:
				sublime.error_message( 'Project directory is not under version control' )
				return

		if not self.svn.is_modified( path ):
			sublime.message_dialog( 'No files have been modified' )
			return

		content = self.svn.get_status( path ).strip()

		if len( content ) == 0:
			return sublime.message_dialog( 'No files to commit' )

		if not self.create_commit_file( content ):
			return sublime.error_message( 'Failed to create commit file' )

		tmp_commits[ self.commit_file_path ] = path

		self.window.open_file( '{0}:0:0' . format( self.commit_file_path ), sublime.ENCODED_POSITION )

	def create_commit_file( self, message ):
		valid_path = False

		for i in range( 100 ):
			i = i if i > 0 else '' # do not append 0 to the commit file name

			file_path = '/tmp/svn-commit{0}.tmp' . format( i )

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
			self.svn.log_error( "Failed to write commit data to '{0}'" . format( file_path ) )
			return False

		self.commit_file_path = file_path

		return True

class SvnCommitSave( sublime_plugin.EventListener ):
	def on_post_save( self, view ):
		if view.file_name() not in tmp_commits:
			return

		self.svn			= SVN( view.window(), validate = False )
		commit_file_path	= view.file_name()
		self.commit_message = ''

		if not self.get_commit_message( commit_file_path ):
			return sublime.error_message( 'Failed to commit file(s)' )

		if len( self.commit_message ) == 0:
			return sublime.message_dialog( 'Did not commit, log message unchanged or not specified' )

		if not self.svn.commit_file( commit_file_path, tmp_commits[ commit_file_path ] ):
			return sublime.error_message( 'Failed to commit file(s)' )

		sublime.status_message( 'SVN: Commited file(s)' )

		del tmp_commits[ commit_file_path ]
		view.close()
		self.delete_commit_file( commit_file_path )

	def on_close( self, view ):
		if view.file_name() not in tmp_commits:
			return

		self.svn	= SVN( view.window(), validate = False )
		file_path 	= view.file_name()

		del tmp_commits[ file_path ]
		self.delete_commit_file( file_path )
		sublime.status_message( "Did not commit '{0}'" . format( file_path ) )

	def get_commit_message( self, file_path ):
		message = ''

		try:
			with open( file_path, 'r' ) as fh:
				for line in fh:
					if line == EDITOR_EOF_PREFIX:
						found = True
						break

					message += line
		except Exception:
			self.svn.log_error( "Failed to read in commit message for file '{0}'" . format( file_path ) )
			return False

		self.commit_message = message.strip()

		return True

	def delete_commit_file( self, file_path ):
		if os.path.isfile( file_path ):
			try:
				os.remove( file_path )
			except:
				self.svn.log_error( "Failed to delete commit file '{0}'" . format( file_path ) )
				return False

		return True

#
# SVN Info Related
#

class SvnInfoCommand( sublime_plugin.WindowCommand ):
	def in_folder( self, file_path ):
		for svn_directory in self.svn_directories:
			length = len( svn_directory )

			if file_path[ 0 : length ] == svn_directory and file_path[ length : length + 1 ] == os.sep:
				return True

		return False

	def run( self, directory = False ):
		self.svn					= SVN( self.window, validate = False )
		self.file_path				= self.window.active_view().file_name()
		self.settings 				= sublime.load_settings( 'mv_svn.sublime-settings' )
		self.svn_directories		= self.settings.get( 'svn_directories', [] )
		self.true_svn_directories	= self.svn_directories_validate()
		self.info_directory			= False
		self.into_file				= True

		if directory:
			self.info_directory		= True
			self.info_file			= False

		if self.info_directory:
			return self.info_directory_quick_panel()

		if not self.in_folder( self.file_path ):
			sublime.error_message( 'File is not in a listed SVN repository' )
			return

		return self.info_file_quick_panel()

	def svn_directories_validate( self ):
		svn_directories = set()

		for svn_directory in self.svn_directories:
			if self.svn.is_tracked( svn_directory ):
				svn_directories.add( svn_directory )

		return list( svn_directories )

	def info_directory_quick_panel( self ):
		self.show_quick_panel( self.true_svn_directories, self.info_directory_callback )

	def info_directory_callback( self, index ):
		pass

	def info_file_quick_panel( self ):
		self.show_quick_panel( [], self.info_file_callback )

	def info_file_callback( self, index ):
		pass

	def top_level_quick_panel( self ):
		if not self.is_tracked:
			self.top_level_entries = [ { 'code': 'af', 'value': 'Add File to Repository' } ]
		else:
			self.top_level_entries = [ { 'code': 'vr', 'value': 'View Revisions' }, { 'code': 'vd', 'value': 'View Differences' } ]

			if self.is_modified:
				self.top_level_entries += [ { 'code': 'cf', 'value': 'Commit File' }, { 'code': 'rf', 'value': 'Revert File' } ]

		self.show_quick_panel( [ entry[ 'value' ] for entry in self.top_level_entries ], self.top_level_callback )

	def top_level_callback( self, index ):
		if index == -1:
			return

		offset	= 0
		code 	= self.top_level_entries[ index - offset ][ 'code' ]

		if code == 'vr':
			return self.revisions_quick_panel()
		elif code == 'vd':
			return self.diff_quick_panel()
		elif code == 'cf':
			return self.window.run_command( 'svn_commit', { 'file': True } )
		elif code == 'rf':
			return self.svn.revert_file( self.file_path )
		elif code == 'af':
			return self.svn.add_file( self.file_path )

	def revisions_quick_panel( self ):
		self.cache_revisions()

		revisions_formatted = [ [ '..' ] ]
		revisions_formatted.extend( self.cached_revisions_formatted )

		self.show_quick_panel( revisions_formatted, self.revision_callback, self.revision_highlight )

	def revision_callback( self, index ):
		self.hide_panel()

		if index == -1:
			return
		elif index == 0:
			return self.top_level_quick_panel()

		offset			= 1
		revision		= self.cached_revisions[ index - offset ]
		current_syntax 	= self.window.active_view().settings().get( 'syntax' )
		view 			= self.window.new_file()

		view.run_command( 'append', { 'characters': self.svn.get_revision_content( self.file_path, revision[ 'number' ] ) } )
		view.set_syntax_file( current_syntax )


	def revision_format( self, revision ):
		return 'r{0} | {1} | {2}' . format( revision[ 'number' ], revision[ 'author' ], revision[ 'date' ] )

	def revision_highlight( self, index ):
		if index == -1:
			return
		elif index == 0:
			return self.show_panel( None )

		offset 		= 1
		revision	= self.cached_revisions[ index - offset ]

		self.show_panel( revision[ 'message' ] )


	def diff_quick_panel( self ):
		self.cache_revisions()

		revisions_formatted = [ [ '..' ] ]

		if self.is_modified:
			revisions_formatted.extend( [ 'Diff Current' ] )

		revisions_formatted.extend( self.cached_revisions_formatted )

		self.show_quick_panel( revisions_formatted, self.diff_callback, self.diff_highlight )

	def diff_callback( self, index ):
		self.hide_panel()

		if index == -1:
			return
		elif index == 0:
			return self.top_level_quick_panel()
		elif index == 1:
			self.window.run_command( 'svn_diff', { 'file': True } )
		else:
			offset		= 2
			revision 	= self.cached_revisions[ index - offset ]
			self.window.run_command( 'svn_diff', { 'file': True, 'revision': revision[ 'number' ] } )

	def diff_highlight( self, index ):
		if index == -1:
			return
		elif index == 0:
			return
		elif index == 1:
			return

		offset 		= 2
		revision 	= self.cached_revisions[ index - offset ]

		self.show_panel( revision[ 'message' ] )


	def cache_revisions( self ):
		if self.cached_revisions:
			return

		self.cached_revisions = self.svn.get_revisions( self.file_path, self.svn.settings.get( 'svn_log_limit', 100 ) )

		for revision in self.cached_revisions:
			self.cached_revisions_formatted.append( self.revision_format( revision ) )

	def show_quick_panel( self, entries, on_select, on_highlight = None ):
		sublime.set_timeout( lambda: self.window.show_quick_panel( entries, on_select, on_highlight = on_highlight ), 10 )

	def show_panel( self, content ):
		if self.svn.settings.get( 'show_panel', True ):
			self.panel = self.window.create_output_panel( 'svn_panel' )
			self.window.run_command( 'show_panel', { 'panel': 'output.svn_panel' } )
			self.panel.set_read_only( False )
			self.panel.run_command( 'append', { 'characters': content } )
			self.panel.set_read_only( True )

	def hide_panel( self ):
		if self.panel:
				self.window.run_command( 'hide_panel', { 'panel': 'output.svn_panel' } )
				self.panel = None

#
# SVN Diff Related
#

class SvnDiffCommand( sublime_plugin.WindowCommand ):
	def run( self, file = False, directory = False, project = False, revision = None, diff_tool = None ):
		self.svn = SVN( self.window )

		if not self.svn.valid or ( file == False and directory == False and project == False ):
			return

		if file:
			if self.svn.file_tracked:
				path = self.svn.current_file
			else:
				sublime.error_message( 'File is not under version control' )
				return
		elif directory:
			if self.svn.directory_tracked:
				path = self.svn.current_directory
			else:
				sublime.error_message( 'Directory is not under version control' )
				return
		elif project:
			if self.svn.project_tracked:
				path = self.svn.current_project
			else:
				sublime.error_message( 'Project directory is not under version control' )
				return

		if not self.svn.is_modified( path ):
			sublime.error_message( 'No files have been modified' )
			return

		if diff_tool is None:
			diff_tool = self.svn.settings.get( 'svn_diff_tool', None )

		self.svn.diff( path, diff_tool, revision )

#
# SVN Update Related
#

class SvnUpdateCommand( sublime_plugin.WindowCommand ):
	def run( self, file = False, directory = False, project = False ):
		self.svn = SVN( self.window )

		if not self.svn.valid or ( file == False and directory == False and project == False ):
			return

		if file:
			if self.svn.file_tracked:
				path = self.svn.current_file
			else:
				sublime.error_message( 'File is not under version control' )
				return
		elif directory:
			if self.svn.directory_tracked:
				path = self.svn.current_directory
			else:
				sublime.error_message( 'Directory is not under version control' )
				return
		elif project:
			if self.svn.project_tracked:
				path = self.svn.current_project
			else:
				sublime.error_message( 'Project directory is not under version control' )
				return

		panel = self.window.create_output_panel( 'svn_panel' )
		self.window.run_command( 'show_panel', { 'panel': 'output.svn_panel' } )
		panel.set_read_only( False )
		panel.run_command( 'insert', { 'characters': self.svn.update( path ) } )
		panel.set_read_only( True )

#
# Helper Classes
#

class SVN():
	def __init__( self, sublime_window, validate = True ):
		self.valid				= False
		self.project_tracked	= False
		self.directory_tracked	= False
		self.file_tracked		= False
		self.current_project	= None
		self.current_directory	= None
		self.current_file		= None
		self.sublime_window		= sublime_window
		self.settings 			= sublime.load_settings( 'mv_svn.sublime-settings' )
		self.svn_binary			= self.settings.get( 'svn', None )

		if self.svn_binary is None:
			sublime.error_message( 'An SVN binary program needs to be set in user settings!' )
			return
		elif not os.access( self.svn_binary, os.X_OK ):
			sublime.error_message( 'The SVN binary needs to be executable!' )
			return

		if validate:
			self.setup()

	def setup( self ):
		if self.sublime_window.active_view().file_name() is not None:
			self.current_file		= self.sublime_window.active_view().file_name()
			self.current_directory	= os.path.dirname( self.sublime_window.active_view().file_name() )

		if self.sublime_window.project_file_name() is not None:
			self.current_project = os.path.dirname( self.sublime_window.project_file_name() )

		if self.current_project is None and self.current_directory is None and self.current_file is None:
			sublime.error_message( 'Could not deduce a valid SVN repository' )
			return

		if self.current_project:
			self.project_tracked 	= self.is_tracked( self.current_project )

		if self.current_directory:
			self.directory_tracked 	= self.is_tracked( self.current_directory )

		if self.current_file:
			self.file_tracked		= self.is_tracked( self.current_file )

		self.valid = True

	def get_revisions( self, path, limit = None ):
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
			revisions.append( { 'number': child.attrib['revision'], 'author': child[ 0 ].text, 'date': child[ 1 ].text, 'message': child[ 2 ].text.strip() } )

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
		returncode, output, error = self.run_command( 'info --xml {0}' . format( shlex.quote( file_path ) ) )

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
					return True

			except KeyError:
				self.log_error( 'Failed to find path attribute' )

		return False

	def is_modified( self, file_path ):
		returncode, output, error = self.run_command( 'status --xml {0}' . format( shlex.quote( file_path ) ) )

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
					return True
			except KeyError:
				self.log_error( 'Failed to find path attribute' )

		return False

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

	def commit_file( self, commit_file_path, path ):
		if not os.path.isfile( commit_file_path ):
			self.log_error( "Failed to find commit file '{0}'" . format( commit_file_path ) )
			return False

		returncode, output, error = self.run_command( 'commit --file={0} {1}' . format( commit_file_path, shlex.quote( path ) ) )

		if returncode != 0:
			self.log_error( error )
			return False

		return True

	def diff( self, path, diff_tool = None, revision = None ):
		command		= ''

		if revision:
			command += '--revision={0}' . format( revision )

		if diff_tool:
			command 		+= ' diff --diff-cmd={0} {1}' . format( diff_tool, shlex.quote( path ) )
			in_background 	= True
		else:
			command 		+= ' diff {0}' . format( shlex.quote( path ) )
			in_background	= False

		returncode, output, error = self.run_command( command, in_background = in_background )

		if returncode != 0:
			self.log_error( error )

		if diff_tool:
			return

		self.sublime_window.new_file().run_command( 'append', { 'characters': output } )

	def update( self, path ):
		returncode, output, error = self.run_command( 'update {0}' . format( shlex.quote( path ) ) )

		if returncode != 0:
			self.log_error( error )
			return ''

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

	def log_error( self, error ):
		if self.settings.get( 'svn_log_errors', False ):
			print( error )

#
# Helper Functions
#
