import sublime, sublime_plugin
import subprocess
import os
import re
import xml.etree.ElementTree as ET

tmp_commits			= dict()
EDITOR_EOF_PREFIX 	= '--This line, and those below, will be ignored--\n'

#
# SVN Commit Related
#

class SvnCommitCommand( sublime_plugin.WindowCommand ):
	def run( self, file = False, project = False ):
		if file == False and project == False:
			return

		self.commit_file_path	= None
		svn	 					= SVN( self.window )

		if svn.project_directory == None:
			return

		if file:
			location = self.window.active_view().file_name()
		else:
			location = svn.project_directory

		content = svn.get_status( location ).strip()

		if len( content ) == 0:
			return sublime.message_dialog( 'No files to commit' )

		if not self.create_commit_file( content ):
			return sublime.error_message( 'Failed to create commit file' )

		tmp_commits[ self.commit_file_path ] = location

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
			self.log_error( 'Failed to create a unique file name' )
			return False

		try:
			with open( file_path, 'w' ) as fh:
				fh.write( '\n' )
				fh.write( EDITOR_EOF_PREFIX )
				fh.write( '\n' )
				fh.write( message )
		except Exception:
			self.log_error( "Failed to write commit data to '{0}'" . format( file_path ) )
			return False

		self.commit_file_path = file_path

		return True

	def log_error( error ):
		print( "The following error occurred: '{0}'" . format( error.strip() ) )

class SvnCommitSave( sublime_plugin.EventListener ):
	def on_post_save( self, view ):
		if view.file_name() not in tmp_commits:
			return

		svn 				= SVN( view.window() )
		file_path			= view.file_name()
		self.commit_message = ''

		if not svn.project_directory:
			return

		if not self.get_commit_message( file_path ):
			return sublime.message_dialog( 'Failed to commit file(s)' )

		if len( self.commit_message ) == 0:
			return sublime.message_dialog( 'Did not commit, log message unchanged or not specified' )

		if not svn.commit_file( file_path, tmp_commits[ file_path ] ):
			return sublime.message_dialog( 'Failed to commit file(s)' )

		sublime.status_message( 'SVN: Commited file(s)' )

		del tmp_commits[ file_path ]
		view.close()
		self.delete_commit_file( file_path )

	def on_close( self, view ):
		if view.file_name() not in tmp_commits:
			return

		file_path = view.file_name()

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
			log_error( "Failed to read in commit message for file '{0}'" . format( file_path ) )
			return False

		self.commit_message = message.strip()

		return True

	def delete_commit_file( self, file_path ):
		if os.path.isfile( file_path ):
			try:
				os.remove( file_path )
			except:
				log_error( "Failed to delete commit file '{0}'" . format( file_path ) )
				return False

		return True

#
# SVN Info Related
#

class SvnInfoCommand( sublime_plugin.WindowCommand ):
	def run( self ):
		self.file_path 					= self.window.active_view().file_name()
		self.svn_directory				= None
		self.is_tracked					= False
		self.is_modified				= False
		self.panel						= None
		self.cached_revisions 			= []
		self.cached_revisions_formatted = []
		self.top_level_entries			= []
		self.cached_diff_entries		= []
		self.settings					= sublime.load_settings( 'mv_svn.sublime-settings' )
		self.svn						= SVN( self.window )

		if self.svn.project_directory == None:
			return

		self.is_tracked			= self.svn.is_tracked( self.file_path )

		if self.is_tracked:
			self.is_modified	= self.svn.is_modified( self.file_path )

		self.top_level_quick_panel()

	def top_level_quick_panel( self ):
		if not self.is_tracked:
			self.top_level_entries = [ { 'code': 'af', 'value': 'Add File to Repository' } ]
		else:
			self.top_level_entries = [ { 'code': 'vr', 'value': 'View Revisions' } ]

			if self.is_modified:
				self.top_level_entries += [ { 'code': 'cf', 'value': 'Commit File' }, { 'code': 'rf', 'value': 'Revert File' }, { 'code': 'vd', 'value': 'View Differences' } ]

		self.show_quick_panel( [ entry[ 'value' ] for entry in self.top_level_entries ], self.top_level_callback )

	def top_level_callback( self, index ):
		if index == -1:
			return

		code = self.top_level_entries[ index ][ 'code' ]

		if code == 'vr':
			return self.revisions_quick_panel()
		elif code == 'vd':
			return self.diff_quick_panel()
		elif code == 'cf':
			return self.commit_file()
		elif code == 'rf':
			return self.svn.revert_file( self.file_path )
		elif code == 'af':
			return self.svn.add_file( self.file_path )

	def revisions_quick_panel( self ):
		self.cache_revisions()

		revisions_formatted = [ [ '..', '' ] ]
		revisions_formatted.extend( self.cached_revisions_formatted )

		self.show_quick_panel( revisions_formatted, self.revision_callback, self.revision_highlight )

	def revision_callback( self, index ):
		self.hide_panel()

		if index == -1:
			return
		elif index == 0:
			return self.top_level_quick_panel()

		current_syntax 	= self.window.active_view().settings().get( 'syntax' )
		view 			= self.window.new_file()

		view.run_command( 'append', { 'characters': self.svn.get_revision_content( self.file_path, self.cached_revisions[ index - 1 ][ 'revision' ] ) } )
		view.set_syntax_file( current_syntax )


	def revision_format( self, revision ):
		return [ 'r{0} | {1} | {2}' . format( revision[ 'revision' ], revision[ 'author' ], revision[ 'date' ] ), revision[ 'message' ] ]

	def revision_highlight( self, index ):
		if index == -1:
			return
		elif index == 0:
			self.show_panel( None )
		else:
			self.show_panel( self.cached_revisions[ index - 1 ][ 'message' ] )


	def diff_quick_panel( self ):
		self.cache_revisions()

		revisions_formatted = [ [ '..', '' ], [ 'Diff Current', '' ] ]
		revisions_formatted.extend( self.cached_revisions_formatted )

		self.show_quick_panel( revisions_formatted, self.diff_callback )

	def diff_callback( self, index ):
		if index == -1:
			return
		elif index == 0:
			return self.top_level_quick_panel()
		elif index == 1:
			self.window.run_command( 'svn_diff', { 'file': True } )
		else:
			self.window.run_command( 'svn_diff', { 'file': True, 'revision': self.cached_revisions[ index - 2 ][ 'revision' ] } )		

	def cache_revisions( self ):
		if self.cached_revisions:
			return

		self.cached_revisions = self.svn.get_revisions( self.file_path )

		for revision in self.cached_revisions:
			self.cached_revisions_formatted.append( self.revision_format( revision ) )

	def commit_file( self ):
		self.window.run_command( 'svn_commit', { 'commit_files': [ self.file_path ] } )

	def show_quick_panel( self, entries, on_select, on_highlight = None ):
		sublime.set_timeout( lambda: self.window.show_quick_panel( entries, on_select, on_highlight = on_highlight ), 10 )

	def show_panel( self, content ):
		if self.settings.get( 'show_panel', True ):
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

#
# SVN Update Related
#

class SvnUpdateCommand( sublime_plugin.WindowCommand ):
	def run( self, file = False, project = False ):
		if file == False and project == False:
			return

		project_directory, file_path 	= setup( self.window )
		svn 							= SVN()

		if project_directory == None:
			return

		if file and file_path == None:
			sublime.message_dialog( 'File is not under version control' )
			return

		if file:
			location = file_path
		else:
			location = project_directory

		panel = self.window.create_output_panel( 'svn_panel' )
		self.window.run_command( 'show_panel', { 'panel': 'output.svn_panel' } )
		panel.set_read_only( False )
		panel.run_command( 'insert', { 'characters': svn.update_location( location ) } )
		panel.set_read_only( True )

class SvnDiffCommand( sublime_plugin.WindowCommand ):
	def run( self, file = False, project = False, revision = None ):
		if file == False and project == False:
			return

		svn 		= SVN( self.window )
		file_name	= self.window.active_view().file_name()

		if file:
			location = file_name
		else:
			location = svn.project_directory

		if not svn.is_tracked( location ):
			sublime.message_dialog( "'{0}' is not under version control" . format( location ) )
			return

		svn.diff_location( self.window, location, revision )

#
# Helper Classes
#

class SVN():
	def __init__( self, sublime_window ):
		self.project_directory	= None
		self.current_file_path	= None
		self.sublime_window		= sublime_window
		self.settings 			= sublime.load_settings( 'mv_svn.sublime-settings' )

		self.setup()

	def setup( self ):
		project_file_name 	= self.sublime_window.project_file_name()
		project_file_name	= '/home/dcarver/repos/test/null.txt'
		project_directory 	= os.path.dirname( project_file_name )

		if not self.is_tracked( project_directory ):
			sublime.error_message( 'Current project is not tracked by SVN' )
			return

		self.project_directory = project_directory

	def get_revisions( self, file_path ):
		revisions					= []
		returncode, output, error 	= self.run_command( 'svn log --xml {0}' . format( file_path ) )

		if returncode != 0:
			self.log_error( error )
			return []

		try:
			root = ET.fromstring( output )
		except ET.ParseError:
			self.log_error( 'Failed to parse XML' )
			return []

		for child in root.iter( 'logentry' ):
			revisions.append( { 'revision': child.attrib['revision'], 'author': child[ 0 ].text, 'date': child[ 1 ].text, 'message': child[ 2 ].text.strip() } )

		return revisions

	def get_revision_content( self, file_path, revision ):
		returncode, output, error = self.run_command( 'svn cat -r{0} {1}' . format( revision, file_path ) )

		if returncode != 0:
			self.log_error( error )
			return ''

		return output

	def get_status( self, path, quiet = True, xml = False ):
		command = 'svn status'

		if quiet:
			command += ' --quiet'

		if xml:
			command += ' --xml'

		command += ' {0}' . format( path )

		returncode, output, error = self.run_command( command )

		if returncode != 0:
			svn.log_error( error )
			return ''

		return output


	def is_tracked( self, file_path ):
		returncode, output, error = self.run_command( 'svn info --xml {0}' . format( file_path ) )

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
		returncode, output, error = self.run_command( 'svn status --xml {0}' . format( file_path ) )

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
		pass

	def revert_file( self, file_path ):
		if not sublime.ok_cancel_dialog( 'Are you sure you want to revert file:\n\n{0}' . format( file_path ), 'Yes, revert' ):
			sublime.status_message( 'File not reverted' )
			return

		returncode, output, error = self.run_command( 'svn revert {0}' . format( file_path ) )

		if returncode != 0:
			self.log_error( error )
			sublime.error_message( 'Failed to revert file' )

		sublime.status_message( 'Reverted file' )

	def commit_file( self, commit_file_path, location ):
		if not os.path.isfile( commit_file_path ):
			self.log_error( "Failed to find commit file '{0}'" . format( commit_file_path ) )
			return False

		returncode, output, error = self.run_command( 'svn commit --file={0} {1}' . format( commit_file_path, location ) )

		if returncode != 0:
			self.log_error( error )
			return False

		return True

	def diff_location( self, sublime_window, location, revision = None ):
		diff_tool 	= self.settings.get( 'diff', '' ).strip()
		command		= ''

		if revision:
			command += '--revision={0}' . format( revision )

		if diff_tool:
			command += ' diff --diff-cmd={0} {1}' . format( diff_tool, location )
		else:
			command += ' diff {0}' . format( location )

		returncode, output, error = self.run_command( 'svn {0}' . format( command ) )

		if returncode != 0:
			self.log_error( error )

		if diff_tool:
			return

		sublime_window.new_file().run_command( 'append', { 'characters': output } )

	def update_location( self, location ):
		returncode, output, error = self.run_command( 'svn update {0}' . format( location ) )

		if returncode != 0:
			self.log_error( error )
			return ''

		return output

	def run_command( self, command ):
		if self.settings.get( 'log_svn_commands', False ):
			print(command)

		return run_command( command )

	def log_error( self, error ):
		if self.settings.get( 'log_svn_errors', False ):
			print(error)

#
# Helper Functions
#

def run_command( command ):
	process			= subprocess.Popen( command, stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell = True, cwd = '/tmp' )
	stdout, stderr	= process.communicate()
	stdout 			= stdout.decode()
	stderr 			= stderr.decode()

	return process.returncode, stdout, stderr

def log_error( error ):
	print( "The following error occurred: '{0}'" . format( error.strip() ) )
	return
