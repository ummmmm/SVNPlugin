import sublime
import os
import shlex
import xml.etree.ElementTree as ET
import subprocess
import json
import collections

from .settings import Settings

class SVN():
	def __init__( self, path = None, binary = '/usr/bin/svn', log_commands = False, log_errors = False ):
		self.path				= None
		self.binary				= binary
		self.log_errors			= log_errors
		self.log_commands		= log_commands
		self.valid				= False
		self.settings			= Settings()
		self.cached_path_info	= dict()
		self.directories		= self.valid_directories()
		self.results			= dict()

		if self.binary is None:
			sublime.error_message( 'An SVN binary program needs to be set in user settings!' )
			return
		elif not os.access( self.binary, os.X_OK ):
			sublime.error_message( 'The SVN binary needs to be executable!' )
			return

		self.valid				= True

	def change_path( self, path ):
		self.path = path

	def info( self, path ):
		self.run_command( 'info --xml {0}' . format( shlex.quote( path ) ) )

		if self.results[ 'returncode' ] != 0:
			return False

		return True

	def log( self, revision = None ):
		if revision is None:
			return self.run_command( 'log --xml {0}' . format( shlex.quote( self.path ) ) )
		
		return self.run_command( 'log --xml --revision={0} {1}' . format( revision, shlex.quote( self.path ) ) )

	def add( self ):
		return self.run_command( 'add {0}' . format( shlex.quote( self.path ) ) )

	def remove( self ):
		return self.run_command( 'remove {0}' . format( shlex.quote( self.path ) ) )

	def revert( self ):
		return self.run_command( 'revert {0}' . format( shlex.quote( self.path ) ) )

	def valid_directories( self ):
		directories 		= set()

		return list( directories )

	def get_revisions( self, path, limit = None ):
		if self.revision_is_cached( path ):
			return self.revision_get_cached( path )

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

		for child in root.getiterator( 'logentry' ):
			revisions.append( { 'path': path, 'number': child.get( 'revision', '' ), 'author': child.findtext( 'author', '' ), 'date': child.findtext( 'date', '' ), 'message': child.findtext( 'msg', '' ) } )

		self.revision_cache_path( path, revisions )

		return revisions

	def revision_is_cached( self, path ):
		cache_path = self.revisions_build_cache_path( path )

		try:
			if os.path.isfile( cache_path ):
				return True
		except:
			pass

		return False

	def revision_get_cached( self, path ):
		cache_path = self.revisions_build_cache_path( path )

		try:
			with open( cache_path, 'r' ) as data_file:
				return json.load( data_file )
		except:
			return []

	def revisions_build_cache_path( self, path ):
		new_path		= path.replace( self.get_svn_directory( path ) + os.sep, '' )
		svnplugin_dir 	= os.path.join( sublime.cache_path(), 'SVNPlugin' )
		
		return os.path.join( svnplugin_dir, '{0}.cache' . format( new_path ) )

	def revision_cache_path( self, path, revisions ):
		cache_path 	= self.revisions_build_cache_path( path )
		dirs 		= os.path.dirname( cache_path )

		if not os.path.isdir( dirs ):
			try:
				os.makedirs( dirs )
			except:
				return

		with open( cache_path, 'w+' ) as fh:
			fh.write( json.dumps( revisions ) )

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
			self.log_error( error )
			return ''

		return output

	def is_tracked( self, file_path = None ):
		if file_path is None:
			file_path = self.path

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

	def is_cached( self, path ):
		return os.path.isfile( self.revisions_build_cache_path( path ) )

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
			return False, None

		files_to_commit = '' # passed in paths will be a set of 1 or more items

		for path in paths:
			files_to_commit += ' {0}' . format( shlex.quote( path ) )

		returncode, output, error = self.run_command( 'commit --file={0} {1}' . format( commit_file_path, files_to_commit ) )

		if returncode != 0:
			self.log_error( error )
			return False, None

		return True, output

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
			command += ' diff --diff-cmd={0} {1}' . format( shlex.quote( diff_tool ), shlex.quote( path ) )
			self.run_command( command, in_background = True )
			return ''

		command 		+= ' diff {0}' . format( shlex.quote( path ) )
		returncode, output, error = self.run_command( command )

		if returncode != 0:
			self.log_error( error )
			return ''

		return output

	def update( self, path ):
		self.run_command( 'update {0}' . format( shlex.quote( path ) ) )

		if self.results[ 'returncode' ] != 0:
			return False

		return True

	def status( self, path ):
		self.run_command( 'status --xml {0}' . format( shlex.quote( path ) ) )

		if self.results[ 'returncode' ] != 0:
			return False

		return True

	def run_command( self, command, in_background = False ):
		command = '{0} {1}' . format( self.binary, command )

		print( command )

		if in_background:
			subprocess.Popen( command, shell = True, cwd = '/tmp' )

			self.results = { 'returncode': 0, 'stdout': '', 'stderr': '' }

			return

		process			= subprocess.Popen( command, stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell = True, cwd = '/tmp' )
		stdout, stderr	= process.communicate()
		stdout 			= stdout.decode()
		stderr 			= stderr.decode()
		
		self.results = { 'returncode': process.returncode, 'stdout': stdout, 'stderr': stderr }

		return

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
		if self.log_errors:
			print( error )
