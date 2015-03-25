import sublime
import os
import shlex
import xml.etree.ElementTree as ET
import subprocess
import json
import collections
import re

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
		self.run_command( [ 'info', '--xml', path ] )

		return self.result()

	def log( self, path, limit = None, revision = None ):
		args = [ 'log', '--xml' ]

		if limit is not None:
			args.extend( [ '--limit', limit ] )

		if revision is not None:
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
		self.run_command( [ 'commit', '--file', commit_file_path, path ] )

		return self.result()

	def annotate( self, path, revision ):
		self.run_command( [ 'annotate', '--revision', revision, path ] )

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

	def cat( self, path, revision = None ):
		args = [ 'cat' ]
		if revision is not None:
			args.extend( [ '--revision', revision ] )

		args.append( path )

		self.run_command( args )

		return self.result()

	def update( self, path ):
		self.run_command( [ 'update', path ] )

		return self.result()

	def status( self, path ):
		self.run_command( [ 'status', '--xml', path ] )

		return self.result()

	def run_command( self, args, block = True ):
		args.insert( 0, self.binary )

		escaped_args = []

		for arg in args:
			arg = str( arg )

			if re.search( '^[a-zA-Z0-9/_^\\-\\.:]+$', arg ) == None:
				arg = "'{0}'" . format( arg )

			escaped_args.append( arg )

		command = ' ' . join( escaped_args )

		if self.log_commands:
			print( 'SVN Command:', command )

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
