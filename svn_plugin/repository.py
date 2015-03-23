import sublime

import os
import shlex
import xml.etree.ElementTree as ET
import subprocess
import json
import collections

from .settings 	import Settings
from .svn 		import SVN

class Repository():
	def __init__( self, path = None ):
		self.settings 			= Settings()
		self.svn				= SVN( path = path, binary = self.settings.svn_binary(), log_commands = self.settings.svn_log_commands() )
		self.path 				= path
		self.file				= False
		self.directory			= False
		self.repositories		= set()
		self.current_repository = None
		self.__error			= None

	def valid( self ):
		if type( self.path ) is not str:
			return self.log_error( 'Validation can only be ran with the path is of a str type' )

		self.valid_repositories()

		if len( self.repositories ) == 0:
			return self.log_error( 'No valid SVN repositories defined' )

		try:
			if os.path.isfile( self.path ):
				self.file = True
			elif os.path.isdir( self.path ):
				self.directory = True
			else:
				return self.log_error( 'Path is not a valid SVN repository' )
		except TypeError:
			return self.log_error( 'Not in a valid SVN repository' )

		if self.file:
			self.current_repository = self.file_in_repository()

			if self.current_repository is None:
				return self.log_error( 'File is not in a valid SVN repository' )
		else:
			self.current_repository = self.path

			if self.current_repository not in self.repositories:
				return self.log_error( 'Directory is not in a valid SVN repository' )

		return True

	def is_modified( self ):
		if not self.svn.status( self.path ):
			return self.log_error( self.svn_error )

		try:
			root = ET.fromstring( self.svn_output )
		except ET.ParseError:
			return self.log_error( 'Failed to parse XML' )

		for child in root.iter( 'entry' ):
			for wc_status in child.getiterator( 'wc-status' ):
				value = wc_status.get( 'item' )

				if value == 'added' or value == 'deleted' or value == 'replaced' or value == 'modified' or value == 'merged' or value == 'conflicted':
					return True

		return self.log_error( 'No files have been modified' )

	def is_tracked( self ):
		if not self.svn.info( self.path ):
			if 'not a working copy' in self.svn_error:
				if self.file:
					return self.log_error( 'File is not under version control' )

				return self.log_error( 'Directory is not under version control' )

			return self.log_error( 'The following SVN error occurred: {0} ' . format( self.svn_error ) )

		try:
			root = ET.fromstring( self.svn_output )
		except ET.ParseError:
			return self.log_error( 'Failed to parse XML' )

		for child in root.iter( 'entry' ):
			try:
				if self.path == child.attrib[ 'path' ]:
					return True
			except KeyError:
				return self.log_error( 'Failed to find path attribute' )

		if self.file:
			return self.log_error( 'File is not under version control' )

		return self.log_error( 'Directory is not under version control' )

	def revert( self ):
		return self.svn.revert( self.path )

	def commit( self, commit_file_path ):
		if not os.path.isfile( commit_file_path ):
			return self.log_error( 'Failed to find commit file {0}' . format( commit_file_path ) )

		files_to_commit = ''

		if not isinstance( self.path, collections.Iterable ):
			files_to_commit = self.path
		else:
			for path in self.path:
				files_to_commit += ' {0}' . format( shlex.quote( path ) )

		return self.svn.commit( files_to_commit.strip(), commit_file_path )

	def annotate( self, revision = None ):
		return self.svn.annotate( self.path, revision )

	def diff( self, revision_number = None, diff_tool = None ):
		return self.svn.diff( self.path, revision = revision_number, diff_tool = diff_tool )

	def add( self ):
		return self.svn.add( self.path )

	def log( self, limit = None, revision = None ):
		return self.svn.log( self.path, limit = limit, revision = revision )

	def status( self ):
		return self.svn.status( self.path )

	def update( self ):
		return self.svn.update( self.path )

	def cat( self, revision = None ):
		return self.svn.cat( self.path, revision = revision )

	def valid_repositories( self ):
		valid = set()

		if not self.settings.svn_directories():
			return

		for repository in self.settings.svn_directories():
			if self.svn.info( repository ):
				valid.add( repository )

		self.repositories = valid

	def file_in_repository( self ):
		for repository in self.repositories:
			repository_length = len( repository )

			if self.path.startswith( repository ) and self.path[ repository_length : repository_length + 1 ] == os.sep:
				return repository

		return None

	def log_error( self, error ):
		self.__error = error

		print( error )

		return False

	@property
	def error( self ):
		return self.__error

	@property
	def svn_returncode( self ):
		return self.svn.results[ 'returncode' ]

	@property
	def svn_output( self ):
		return self.svn.results[ 'stdout' ]

	@property
	def svn_error( self ):
		return self.svn.results[ 'stderr' ]
