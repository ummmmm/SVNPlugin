import os
import subprocess
import sublime, sublime_plugin
import re

view_id 		= 0
initial_commit 	= ""

class SvnSaveCommand( sublime_plugin.EventListener ):
	def on_post_save( self, view ):
		global view_id

		if view.buffer_id() != view_id:
			return

		found 	= False
		error 	= None
		message = ""

		with open( '/tmp/svn_commit.tmp') as f:
			for line in f:
				if '--This line, and those below, will be ignored--' in line:
					found = True
					break

				message = message + line

		if not found:
			sublime.error_message( "Did not commit file, failed to find the required text:\n '--This line, and those below, will be ignored--'" )
			return

		if len( message.strip() ) == 0:
			sublime.error_message( 'Did not commit file as the commit message was empty' )
			return

		# output, error = run_svn_command( 'commit -F %s' % view.file_name() )

		if error is not None:
			sublime.error_message( 'Failed to commit file' )
			return error( error )

		sublime.message_dialog( "Commited message" )
		view_id = 0
		view.close()

	def on_pre_close( self, view ):
		if view.buffer_id() != view_id:
			return

		sublime.message_dialog( 'Did not commit' )	

class SvnCommand( sublime_plugin.WindowCommand ):
	def run( self ):
		global view_id
		global initial_commit

		path = "/home/dcarver/public_html/90003/mm5/5.00"
		view = self.window.active_view()

		output, error = run_svn_command( 'info %s' % path )

		if error is not None:
			return error( error )

		svn_url = None

		for line in output.split( "\n" ):
			matches = re.search( "^URL: (.*?)$", line )

			if matches:
				svn_url = matches.group( 1 )
				break

		if svn_url is None:
			print( 'Failed to find SVN URL' )
			return

		output, error = run_svn_command( 'status --quiet', path )

		if error is not None:
			return error( error )

		if len( output ) == 0:
			sublime.message_dialog( 'No files to commit' )
			return

		with open( '/tmp/svn_commit.tmp', 'w+' ) as f:
			f.write( "\n\n" )
			f.write( '--This line, and those below, will be ignored--' )
			f.write( "\n\n" )
			f.write( output )

		new_view 		= self.window.open_file( '/tmp/svn_commit.tmp:0:0', sublime.ENCODED_POSITION )
		view_id 		= new_view.buffer_id()
		initial_commit 	= new_view.substr( sublime.Region( 0, new_view.size() ) )

class SvnMeldCommand( sublime_plugin.WindowCommand ):
	def run( self ):
		if self.window.project_file_name() is None:
			print( 'Must be in a project to run this command' )
			return

		subprocess.Popen( "svn diff --diff-cmd /usr/bin/meld", shell = True, cwd = os.path.dirname( self.window.project_file_name() ) )

def run_svn_command( command, cwd = None ):
	p = subprocess.Popen( "/usr/bin/svn %s" % command, stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell = True, cwd = cwd )
	stdout, stderr = p.communicate()

	print( '/usr/bin/svn %s' % command )

	output 	= stdout.decode()
	error	= stderr.decode()

	if len( error ) == 0:
		return ( output, None )

	return ( output, error )

def error( error ):
	print( 'The following error occurred: \'%s\'' % error.strip() )
	return
