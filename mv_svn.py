import sublime, sublime_plugin
import subprocess
import os
import re
import xml.etree.ElementTree as ET

view_id 			= 0
initial_commit 		= ""
tmp_file			= ""
svn_directory		= '/home/dcarver/test'
EDITOR_EOF_PREFIX 	= '--This line, and those below, will be ignored--\n'

class SvnSaveCommand( sublime_plugin.EventListener ):
	def on_post_save( self, view ):
		global view_id

		if view.buffer_id() != view_id:
			return

		value, message = get_commit_message( tmp_file )

		if not value:
			return sublime.message_dialog( 'Failed to commit file(s), view console to see more info' )

		if not message:
			return sublime.message_dialog( 'Did not commit, log message unchanged or not specified' )

		code, output, error = run_command( 'svn commit -F {0}' . format( tmp_file ), cwd = svn_directory )

		if code:
			sublime.message_dialog( 'Failed to commit file(s)' )
			return log_error( error )

		sublime.message_dialog( 'Commited file(s)' )
		view_id = 0
		view.close()
		delete_commit_file( tmp_file )

	def on_close( self, view ):
		if view.buffer_id() != view_id:
			return

		delete_commit_file( tmp_file )
		sublime.message_dialog( 'Did not commit' )

class SvnCommand( sublime_plugin.WindowCommand ):
	def run( self ):
		global view_id
		global tmp_file
		global initial_commit

		view = self.window.active_view()

		code, output, error = run_command( 'svn info .', cwd = svn_directory )

		if code:
			return log_error( error )

		code, output, error = run_command( 'svn status --quiet', cwd = svn_directory )

		if code:
			return log_error( error )

		if not output:
			return sublime.message_dialog( 'No files to commit' )

		created, file_path = create_commit_file( output )

		if not created:
			return

		tmp_file		= file_path
		tmp_view 		= self.window.open_file( '{0}:0:0' . format( file_path ), sublime.ENCODED_POSITION )
		view_id 		= tmp_view.buffer_id()
		initial_commit 	= tmp_view.substr( sublime.Region( 0, tmp_view.size() ) )

class SvnInfoCommand( sublime_plugin.WindowCommand ):
	def run( self ):
		view 			= self.window.active_view()
		self.file_path 	= view.file_name()
		self.entries	= []
		self.file_path	= '/home/dcarver/test/test.txt'

		if not self.is_tracked():
			return

		self.top_level_quick_panel()

	def top_level_quick_panel( self ):
		self.entries = [ 'View Commit Logs', 'Diff Current Changes', 'Diff at Revision' ]
		self.window.show_quick_panel( self.entries, lambda index: self.top_level_select_entry( self.entries, index ) )

	def top_level_select_entry( self, entries, index ):
		if index == -1:
			return
		elif index == 0:
			return self.view_commit_logs()
		elif index == 1:
			return self.diff_current()
		elif index == 2:
			pass

		log_error( "Invalid top level entry index '{0}'" . format( index ) )

	def diff_current( self ):
		if not self.is_modified():
			return

		code, output, error = run_command( 'svn diff --diff-cmd /usr/bin/meld {0}' . format( self.file_path ), cwd = svn_directory )

		if code != 0:
			log_error( error )

	def view_commit_logs( self ):
		entries = [ '..' ]
		entries +=( get_file_logs( self.file_path ) )

		sublime.set_timeout( lambda: self.window.show_quick_panel( [ self.format_commit_entry( entry ) for entry in entries ], lambda index: self.commit_logs_select_entry( entries, index ) ), 10 )

	def commit_logs_select_entry( self, entries, index ):
		if index == -1:
			return

		entry = entries[ index ]

		if type( entry ) is str and entry == '..':
			sublime.set_timeout( lambda: self.top_level_quick_panel(), 10 )
			return

		content	= self.get_revision( self.file_path, entry[ 'revision' ] )
		view	= self.window.new_file()

		sublime.set_timeout( lambda: self.insert_text( view, content ) )

	def format_commit_entry( self, entry ):
		if type( entry ) is str:
			return [ entry, '' ]

		return [ 'r{0} | {1} | {2}' . format( entry[ 'revision' ], entry[ 'author' ], entry[ 'date' ] ), entry[ 'message' ] ]

	def insert_text( self, view, content ):
		if not view.is_loading():
			view.run_command( 'svn_insert_content', { "content": content } )
		else:
			sublime.set_timeout( lambda: self.insert_text( view, contnet ) )

	def format_entry( self, entry ):
		return [ 'r{0} | {1} | {2}' . format( entry[ 'revision' ], entry[ 'author' ], entry[ 'date' ] ), entry[ 'message' ] ]

	def get_revision( self, file_path, revision ):
		code, output, error = run_command( 'svn cat -r{0} {1}' . format( revision, file_path ) )

		if code != 0:
			log_error( error )
			return ''

		return output

	def is_tracked( self ):
		code, output, error = run_command( 'svn info {0}' . format( self.file_path ) )

		if code != 0:
			log_error( error )
			return False

		return True

	def is_modified( self ):
		code, output, error = run_command( 'svn status {0}' . format( self.file_path ) )

		if code != 0:
			log_error( error )
			return False

		return True

class SvnInsertContentCommand( sublime_plugin.TextCommand ):
	def run( self, edit, content = None ):
		self.view.insert( edit, 0, content )

class SvnMeldCommand( sublime_plugin.WindowCommand ):
	def run( self ):
		run_command( 'svn diff -diff-cmd /usr/bin/meld', cwd = svn_directory )

def create_commit_file( message ):
	valid_path = False

	for i in range( 100 ):
		i = i if i else ''

		file_path = '/tmp/svn-commit{0}.tmp' . format( i )

		if not os.path.isfile( file_path ):
			valid_path = True
			break

	if not valid_path:
		log_error( 'Failed to create a unique file name' )
		return False, None

	try:
		with open( file_path, 'w' ) as fh:
			fh.write( '\n' )
			fh.write( EDITOR_EOF_PREFIX )
			fh.write( '\n' )
			fh.write( message )
	except Exception:
		log_error( "Failed to write commit data to '{0}'" . format( file_path ) )
		return False, None

	return True, file_path

def delete_commit_file( file_path ):
	if os.path.isfile( file_path ):
		try:
			os.remove( file_path )
		except:
			log_error( "Failed to delete commit file '{0}'" . format( file_path ) )
			return False

	return True

def get_commit_message( file_path ):
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

def run_command( command, cwd = None ):
	process			= subprocess.Popen( command, stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell = True, cwd = cwd )
	stdout, stderr	= process.communicate()
	stdout 			= stdout.decode()
	stderr 			= stderr.decode()

	return process.returncode, stdout, stderr

def get_file_logs( file_path ):
	logs				= []
	code, output, error = run_command( 'svn log --xml {0}' . format( file_path ), cwd = svn_directory )

	if code != 0:
		log_error( error )
		return []

	try:
		root = ET.fromstring( output )
	except ET.ParseError:
		log_error( 'Failed to parse XML' )
		return []


	for child in root.iter( 'logentry' ):
		revision 	= child.attrib['revision']
		author		= child[ 0 ].text
		date		= child[ 1 ].text
		message		= child[ 2 ].text
		logs.append( { 'revision': revision, 'author': author, 'date': date, 'message': message.strip() } )

	return logs

def log_error( error ):
	print( 'The following error occurred: \'%s\'' % error.strip() )
	return

