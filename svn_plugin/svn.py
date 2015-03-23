import sublime
import os
import shlex
import xml.etree.ElementTree as ET
import subprocess
import json
import collections

from .settings import Settings

class SVN():
	def __init__( self, path = None, binary = '/usr/bin/svn', log_commands = False ):
		self.path				= None
		self.binary				= binary
		self.log_commands		= log_commands
		self.valid				= False
		self.settings			= Settings()
		self.cached_path_info	= dict()
		self.results			= dict()

		if self.binary is None:
			sublime.error_message( 'An SVN binary program needs to be set in user settings!' )
			return
		elif not os.access( self.binary, os.X_OK ):
			sublime.error_message( 'The SVN binary needs to be executable!' )
			return

		self.valid				= True

	def info( self, path ):
		self.run_command( 'info --xml {0}' . format( shlex.quote( path ) ) )

		return self.result()

	def log( self, path, limit = None, revision = None ):
		command = 'log --xml'

		if limit is not None:
			command += ' --limit={0}' . format( limit )

		if revision is not None:
			command += ' --revision={0}' . format( revision )

		self.run_command( '{0} {1}' . format( command, shlex.quote( path ) ) )

		return self.result()

	def add( self, path ):
		self.run_command( 'add {0}' . format( shlex.quote( path ) ) )

		return self.result()

	def remove( self ):
		self.run_command( 'remove {0}' . format( shlex.quote( self.path ) ) )

		return self.result()

	def revert( self, path ):
		self.run_command( 'revert {0}' . format( shlex.quote( path ) ) )

		return self.result()

	def commit( self, path, commit_file_path ):
		self.run_command( 'commit --file={0} {1}' . format( shlex.quote( commit_file_path ), path ) )

		return self.result()

	def annotate( self, path, revision ):
		self.run_command( 'annotate --revision={0} {1}' . format( revision, shlex.quote( path ) ) )

		return self.result()

	def diff( self, path, revision = None, diff_tool = None ):
		command = 'diff'
		block	= True

		if revision:
			command += ' --revision={0}' . format( revision )

		if diff_tool is not None:
			block	= False
			command += ' --diff-cmd={0}' . format( shlex.quote( diff_tool ) )

		command += ' {0}' . format( shlex.quote( path ) )

		self.run_command( command, block = block )

		if not block:
			return True

		return self.result()

	def cat( self, path, revision = None ):
		if revision is None:
			self.run_command( 'cat {0}' . format( shlex.quote( path ) ) )
		else:
			self.run_command( 'cat --revision={0} {1}' . format( revision, shlex.quote( path ) ) )

		return self.result()

	def update( self, path ):
		self.run_command( 'update {0}' . format( shlex.quote( path ) ) )

		return self.result()

	def status( self, path ):
		self.run_command( 'status --xml {0}' . format( shlex.quote( path ) ) )

		return self.result()

	def run_command( self, command, block = True ):
		command = '{0} {1}' . format( self.binary, command )

		if self.log_commands:
			print( command )

		if not block:
			subprocess.Popen( command, shell = True, cwd = '/tmp' )

			self.results = { 'returncode': 0, 'stdout': '', 'stderr': '' }

			return

		process			= subprocess.Popen( command, stdout = subprocess.PIPE, stderr = subprocess.PIPE, shell = True, cwd = '/tmp' )
		stdout, stderr	= process.communicate()
		stdout 			= stdout.decode()
		stderr 			= stderr.decode()

		self.results = { 'returncode': process.returncode, 'stdout': stdout, 'stderr': stderr }

		return

	def result( self ):
		return True if self.results[ 'returncode' ] == 0 else False
