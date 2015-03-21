import sublime

import os
import shlex
import xml.etree.ElementTree as ET
import subprocess
import json

from .settings 	import Settings
from .svn 		import SVN

class Repository():
	def __init__( self, path ):
		self.settings 		= Settings()
		self.path 			= path
		self.svn			= SVN( path )
		self.file			= False
		self.directory		= False
		self.last_svn_dict 	= dict()
		self.repositories	= set()
		self.__error		= None

	def valid( self ):
		self.valid_repositories()

		if len( self.repositories ) == 0:
			return self.log_error( 'No valid SVN repositories defined' )

		try:
			if os.path.isfile( self.path ):
				self.file = True
			elif os.path.isdir( self.path ):
				self.directory = True
			else:
				return self.log_error( '{0} is not a valid SVN repository' . format( self.path ) )
		except TypeError:
			return self.log_error( 'Not in a valid SVN repository' )

		if self.file:
			if not self.file_in_repository():
				return self.log_error( '{0} is not in a valid SVN repository' . format( self.path ) )
		else:
			if self.path not in self.repositories:
				return self.log_error( '{0} is not in a valid SVN repository' . format( self.path ) )

		return True

	def valid_repositories( self ):
		valid 	= set()
		svn 	= SVN()

		if not self.settings.svn_directories():
			return

		for repository in self.settings.svn_directories():
			if svn.info( repository ):
				valid.add( repository )

		self.repositories = valid

	def file_in_repository( self ):
		for repository in self.repositories:
			repository_length = len( repository )

			if self.path.startswith( repository ) and self.path[ repository_length : repository_length + 1 ] == os.sep:
				return True

		return False

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

	def error( self, error ):
		self.__error = error
		return False

	def revert( self ):
		return self.svn.revert( self.path )

	def commit( self ):
		pass

	def annotate( self ):
		return self.svn.annotate( self.path )

	def diff( self, revision_number = None, diff_tool = None ):
		return self.svn.diff( self.path, revision = revision_number, diff_tool = diff_tool )

	def add( self ):
		return self.svn.add( self.path )

	def status( self ):
		return self.svn.status( self.path )

	def update( self ):
		return self.svn.update( self.path )

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

	def log_error( self, error ):
		self.__error = error

		print( error )

		return False
