import sublime
import os
import subprocess
import shlex

class SVN():
	binary 			= None
	log_commands	= False

	@classmethod
	def init( cls, binary, log_commands ):
		if binary is None:
			raise OSError( 'An SVN binary needs to be configured in the SVNPlugin settings' )
		elif not os.path.isfile( binary ):
			raise OSError( 'SVN binary not found' )
		elif not os.access( binary, os.X_OK ):
			raise OSError( 'SVN binary is not executable' )

		cls.binary 			= binary
		cls.log_commands	= log_commands

	def __init__( self, cwd = '/tmp' ):
		self.cwd		= cwd
		self.results 	= dict()

	def info( self, path ):
		self.run_command( [ 'info', '--xml', path ] )

		return self.result()

	def log( self, path, limit = None, revision = None ):
		args = [ 'log', '--xml' ]

		if limit:
			args.extend( [ '--limit', limit ] )

		if revision:
			args.extend( [ '--revision', revision ] )

		args.append( path )

		self.run_command( args )

		return self.result()

	def add( self, path ):
		self.run_command( [ 'add', path ] )

		return self.result()

	def remove( self ):
		self.run_command( [ 'remove', path ] )

		return self.result()

	def revert( self, path ):
		self.run_command( [ 'revert', path ] )

		return self.result()

	def commit( self, path, commit_file_path ):
		args = [ 'commit', '--file', commit_file_path ]
		args.extend( path )

		self.run_command( args )

		return self.result()

	def annotate( self, path, revision ):
		args = [ 'annotate' ]

		if revision is not None:
			args.extend( [ '--revision', revision ] )

		args.append( path )

		self.run_command( args )

		return self.result()

	def diff( self, path, revision = None, diff_tool = None ):
		args 	= [ 'diff' ]
		block	= True

		if revision:
			args.extend( [ '--revision', revision ] )

		if diff_tool is not None:
			block	= False
			args.extend( [ '--diff-cmd', diff_tool ] )

		args.append( path )

		self.run_command( args, block = block )

		if not block:
			return True

		return self.result()

	def cat( self, path, revision = None):
		args = [ 'cat' ]

		if revision:
			args.extend( [ '--revision', revision ] )

		args.append( path )

		self.run_command( args )

		return self.result()

	def update( self, path ):
		self.run_command( [ 'update', path, '--accept', 'postpone' ] )

		return self.result()

	def status( self, path, xml = True, quiet = False ):
		args = [ 'status' ]

		if xml:
			args.append( '--xml' )

		if quiet:
			args.append( '--quiet' )

		args.append( path )

		self.run_command( args )

		return self.result()

	def ls( self, path ):
		self.run_command( [ 'ls', '--xml', path ] )

		return self.result()

	def run_command( self, args, block = True ):
		args.insert( 0, SVN.binary )

		command = ' '.join( [ shlex.quote( str( arg ) ) for arg in args ] )

		if SVN.log_commands:
			print( 'SVN Command:', command )

		if not block:
			subprocess.Popen( command, shell = True, cwd = self.cwd )

			self.results = { 'returncode': 0, 'stdout': '', 'stderr': '' }

			return

		process			= subprocess.Popen( command, stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell = True, cwd = self.cwd )
		stdout, stderr	= process.communicate()
		stdout 			= stdout.decode()
		stderr 			= stderr.decode()

		self.results = { 'returncode': process.returncode, 'stdout': stdout, 'stderr': stderr }

		return

	def result( self ):
		return True if self.results[ 'returncode' ] == 0 else False
