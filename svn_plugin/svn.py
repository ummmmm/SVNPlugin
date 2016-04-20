import os
import subprocess
import shlex

class SVN():
	binary 			= None
	log_commands	= False

	@classmethod
	def init( cls, binary = None, log_commands = False ):
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
		self.results	= dict()

	def info( self, path ):
		return self.run_command( [ 'info', '--xml', path ] )

	def log( self, path, xml = True, stop_on_copy = True, limit = None, revision = None ):
		args = [ 'log', '--verbose' ]

		if xml:
			args.append( '--xml' )

		if stop_on_copy:
			args.append( '--stop-on-copy' )

		if limit:
			args.extend( [ '--limit', limit ] )

		if revision:
			args.extend( [ '--revision', revision ] )

		args.append( path )

		return self.run_command( args )

	def add( self, path ):
		return self.run_command( [ 'add', path ] )

	def remove( self ):
		return self.run_command( [ 'remove', path ] )

	def revert( self, path ):
		return self.run_command( [ 'revert', path ] )

	def commit( self, paths, commit_file_path ):
		args = [ 'commit', '--file', commit_file_path ]
		args.extend( paths )

		return self.run_command( args )

	def annotate( self, path, revision ):
		args = [ 'annotate' ]

		if revision is not None:
			args.extend( [ '--revision', revision ] )

		args.append( path )

		return self.run_command( args )

	def diff( self, path, revision = None, diff_tool = None ):
		args 	= [ 'diff' ]
		block	= False if diff_tool else True

		if revision:
			args.extend( [ '--revision', revision ] )

		if diff_tool:
			args.extend( [ '--diff-cmd', diff_tool ] )

		args.append( path )

		return self.run_command( args, block = block )

	def cat( self, path, revision = None):
		args = [ 'cat' ]

		if revision:
			args.extend( [ '--revision', revision ] )

		args.append( path )

		return self.run_command( args )

	def update( self, path ):
		return self.run_command( [ 'update', path, '--accept', 'postpone' ] )

	def status( self, path, xml = True, quiet = False ):
		args = [ 'status' ]

		if xml:
			args.append( '--xml' )

		if quiet:
			args.append( '--quiet' )

		args.append( path )

		return self.run_command( args )

	def ls( self, path ):
		return self.run_command( [ 'ls', '--xml', path ] )

	def run_command( self, args, block = True ):
		args.insert( 0, SVN.binary )

		command = ' '.join( [ shlex.quote( str( arg ) ) for arg in args ] )

		if SVN.log_commands:
			print( 'SVN Command:', command )

		if not block:
			subprocess.Popen( command, shell = True, cwd = self.cwd )

			self.results = { 'returncode': 0, 'stdout': '', 'stderr': '' }

			return True

		process			= subprocess.Popen( command, stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell = True, cwd = self.cwd )
		stdout, stderr	= process.communicate()
		stdout 			= stdout.decode()
		stderr 			= stderr.decode()

		self.results = { 'returncode': process.returncode, 'stdout': stdout, 'stderr': stderr }

		return True if self.results[ 'returncode' ] == 0 else False
