import sublime, sublime_plugin
import subprocess
import os
import re
import xml.etree.ElementTree as ET

tmp_commit_files	= set()
svn_directory		= '/home/dcarver/test'
commit_files		= []
EDITOR_EOF_PREFIX 	= '--This line, and those below, will be ignored--\n'

#
# SVN Commit Related
#

class SvnCommitCommand( sublime_plugin.WindowCommand ):
	def run( self, commit_files = [] ):
		self.commit_file_path = ''

		returncode, output, error = run_command( 'svn status --quiet', cwd = svn_directory )

		if returncode:
			return log_error( error )

		if not output:
			return sublime.message_dialog( 'No files to commit' )

		if not self.create_commit_file( output ):
			return sublime.error_message( 'Failed to create commit file' )

		self.window.open_file( '{0}:0:0' . format( self.commit_file_path ), sublime.ENCODED_POSITION )
		tmp_commit_files.add( self.commit_file_path )

	def create_commit_file( self, message ):
		valid_path = False

		for i in range( 100 ):
			i = i if i > 0 else '' # do not append 0 to the commit file name

			file_path = '/tmp/svn-commit{0}.tmp' . format( i )

			if not os.path.isfile( file_path ):
				valid_path = True
				break

		if not valid_path:
			log_error( 'Failed to create a unique file name' )
			return False

		try:
			with open( file_path, 'w' ) as fh:
				fh.write( '\n' )
				fh.write( EDITOR_EOF_PREFIX )
				fh.write( '\n' )
				fh.write( message )
		except Exception:
			log_error( "Failed to write commit data to '{0}'" . format( file_path ) )
			return False

		self.commit_file_path = file_path

		return True

class SvnCommitSave( sublime_plugin.EventListener ):
	def on_post_save( self, view ):
		if not view.file_name() in tmp_commit_files:
			return

		value, message = self.get_commit_message( view.file_name() )

		if not value:
			return sublime.message_dialog( 'Failed to commit file(s), view console to see more info' )

		if not message:
			return sublime.message_dialog( 'Did not commit, log message unchanged or not specified' )

		returncode, output, error = run_command( 'svn commit -F {0}' . format( view.file_name() ), cwd = svn_directory )

		if returncode != 0:
			sublime.message_dialog( 'Failed to commit file(s)' )
			return log_error( error )

		sublime.status_message( 'MvSVN: Commited file(s)' )

		tmp_commit_files.remove( view.file_name() )
		view.close()
		self.delete_commit_file( view.file_name() )

	def on_close( self, view ):
		if not view.file_name() in tmp_commit_files:
			return

		tmp_commit_files.remove( view.file_name() )
		self.delete_commit_file( view.file_name() )
		sublime.status_message( "MvSVN: Did not commit '{0}'" . format( view.file_name() ) )

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
			return False, None

		return True, message.strip()

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
		self.file_path					= '/home/dcarver/test/test.txt'
		self.panel						= None
		self.cached_revisions 			= []
		self.cached_revisions_formatted = []
		self.top_level_entries			= []
		self.cached_diff_entries		= []
		self.svn						= SVN()
		self.settings					= sublime.load_settings( 'mv_svn.sublime-settings' )

		self.top_level_quick_panel()

	def top_level_quick_panel( self ):
		if not self.is_tracked():
			self.top_level_entries = [ { 'code': 'af', 'value': 'Add File to Repository' } ]
		else:
			self.top_level_entries = [ { 'code': 'vr', 'value': 'View Revisions' } ]

			if self.is_modified():
				self.top_level_entries += [ { 'code': 'cf', 'value': 'Commit File' }, { 'code': 'rf', 'value': 'Revert File' }, { 'code': 'vd', 'value': 'View Differences' } ]

		self.show_quick_panel( [ entry[ 'value' ] for entry in self.top_level_entries ], self.top_level_select_entry )

	def diff_quick_panel( self ):
		if not self.cached_diff_entries:
			self.cached_diff_entries = [ 'Diff at Current', 'Diff at Revision' ]

		self.show_quick_panel( self.cached_diff_entries, None )

	def top_level_select_entry( self, index ):
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
			return self.revert_file()
		elif code == 'af':
			return self.add_file()

		log_error( "Invalid top level entry code '{0}'" . format( code ) )

	def commit_file( self ):
		self.window.run_command( 'svn_commit', { 'commit_files': [ self.file_path ] } )

	def add_file( self ):
		pass

	def revert_file( self ):
		if not sublime.ok_cancel_dialog( 'Are you sure you want to revert file:\n\n{0}' . format( self.file_path ), 'Yes, revert' ):
			sublime.status_message( 'File not reverted' )
			return

		returncode, output, error = run_command( 'svn revert {0}' . format( self.file_path ) )

		if returncode != 0:
			log_error( error )
			sublime.error_message( 'Failed to revert file' )

		sublime.status_message( 'Reverted file' )

	def view_diff( self ):
		if not self.is_modified():
			return

		returncode, output, error = run_command( 'svn diff --diff-cmd /usr/bin/meld {0}' . format( self.file_path ), cwd = svn_directory )

		if returncode != 0:
			log_error( error )

	def revisions_quick_panel( self ):
		if not self.cached_revisions:
			self.cached_revisions = self.svn.get_revisions( self.file_path )

			for revision in self.cached_revisions:
				self.cached_revisions_formatted.append( self.format_revision( revision ) )

		revisions_formatted = [ [ '..', '' ] ]
		revisions_formatted.extend( self.cached_revisions_formatted )

		self.show_quick_panel( revisions_formatted, self.revision_list_callback, self.revision_highlight )

	def show_quick_panel( self, entries, on_select, on_highlight = None ):
		sublime.set_timeout( lambda: self.window.show_quick_panel( entries, on_select, on_highlight = on_highlight ), 10 )

	def revision_highlight( self, index ):
		if index == -1:
			return
		elif index == 0:
			self.show_panel( None )
		else:
			self.show_panel( self.cached_revisions[ index ][ 'message' ] )

	def revision_list_callback( self, index ):
		self.hide_panel()

		if index == -1:
			return
		elif index == 0:
			return self.top_level_quick_panel()

		self.window.new_file().run_command( 'append', { 'characters': self.svn.get_revision_content( self.file_path, self.cached_revisions[ index ][ 'revision' ] ) } )

	def hide_panel( self ):
		if self.panel:
				self.window.run_command( 'hide_panel', { 'panel': 'output.svn_panel' } )
				self.panel = None

	def show_panel( self, content ):
		if self.settings.get( 'show_panel', True ):
			self.panel = self.window.create_output_panel( 'svn_panel' )
			self.window.run_command( 'show_panel', { 'panel': 'output.svn_panel' } )
			self.panel.set_read_only( False )
			self.panel.run_command( 'append', { 'characters': content } )
			self.panel.set_read_only( True )

	def format_revision( self, revision ):
		return [ 'r{0} | {1} | {2}' . format( revision[ 'revision' ], revision[ 'author' ], revision[ 'date' ] ), revision[ 'message' ] ]

	def is_tracked( self ):
		returncode, output, error = run_command( 'svn info --xml {0}' . format( self.file_path ) )

		if returncode != 0:
			log_error( error )
			return False

		try:
			root = ET.fromstring( output )
		except ET.ParseError:
			log_error( 'Failed to parse XML' )
			return False

		for child in root.iter( 'entry' ):
			try:
				if self.file_path == child.attrib[ 'path' ]:
					return True

			except KeyError:
				log_error( 'Failed to find path attribute' )

		return False

	def is_modified( self ):
		returncode, output, error = run_command( 'svn status --xml {0}' . format( self.file_path ) )

		if returncode != 0:
			log_error( error )
			return False

		try:
			root = ET.fromstring( output )
		except ET.ParseError:
			log_error( 'Failed to parse XML' )
			return False

		for child in root.iter( 'entry' ):
			try:
				if self.file_path == child.attrib[ 'path' ]:
					return True
			except KeyError:
				log_error( 'Failed to find path attribute' )

		return False

#
# Helper Classes
#

class SvnMeldCommand( sublime_plugin.WindowCommand ):
	def run( self ):
		view = self.window.active_view()

		returncode, output, error = run_command( 'svn diff --diff-cmd /usr/bin/meld', cwd = svn_directory )

		if returncode != 0:
			log_error( error )

class SVN():
	def __init__( self ):
		pass

	def run_command( self, command ):
		return run_command( 'svn {0}' . format( command ), cwd = svn_directory )

	def get_revisions( self, file_path ):
		revisions					= []
		returncode, output, error 	= run_command( 'svn log --xml {0}' . format( file_path ) )

		if returncode != 0:
			log_error( error )
			return []

		try:
			root = ET.fromstring( output )
		except ET.ParseError:
			log_error( 'Failed to parse XML' )
			return []

		for child in root.iter( 'logentry' ):
			revisions.append( { 'revision': child.attrib['revision'], 'author': child[ 0 ].text, 'date': child[ 1 ].text, 'message': child[ 2 ].text.strip() } )

		return revisions

	def get_revision_content( self, file_path, revision ):
		returncode, output, error = run_command( 'svn cat -r{0} {1}' . format( revision, file_path ) )

		if returncode != 0:
			log_error( error )
			return ''

		return output
#
# Helper Functions
#

def run_command( command, cwd = None ):
	process			= subprocess.Popen( command, stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell = True, cwd = cwd )
	stdout, stderr	= process.communicate()
	stdout 			= stdout.decode()
	stderr 			= stderr.decode()

	return process.returncode, stdout, stderr

def log_error( error ):
	print( "The following error occurred: '{0}'" . format( error.strip() ) )
	return
