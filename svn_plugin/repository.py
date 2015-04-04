import os
import xml.etree.ElementTree as ET
import json

from .settings 	import Settings
from .svn 		import SVN

class Repository():
	def __init__( self, path ):
		self.settings 			= Settings()
		self.svn				= SVN()
		self.path 				= path
		self.__error			= None

	def is_modified( self ):
		if not self.svn.status( self.path ):
			return self.log_error( self.svn_error )

		try:
			root = ET.fromstring( self.svn_output )
		except ET.ParseError:
			return self.log_error( 'Failed to parse XML' )

		for child in root.getiterator( 'entry' ):
			for wc_status in child.getiterator( 'wc-status' ):
				value = wc_status.get( 'item' )

				if value in ( 'added', 'deleted', 'replaced', 'modified', 'merged', 'conflicted' ):
					return True

		return False

	def is_tracked( self ):
		if not self.svn.info( self.path ):
			if 'not a working copy' in self.svn_error:
				return self.log_error( '{0} is not under version control'.format( self.path ) )

			return self.log_error( 'The following SVN error occurred: {0} ' . format( self.svn_error ) )

		try:
			root = ET.fromstring( self.svn_output )
		except ET.ParseError:
			return self.log_error( 'Failed to parse XML' )

		for child in root.getiterator( 'entry' ):
			try:
				if self.path == child.attrib[ 'path' ]:
					return True
			except KeyError:
				return self.log_error( 'Failed to find path attribute' )

		return False

	def revert( self ):
		return self.svn.revert( self.path )

	def commit( self, commit_file_path ):
		if not os.path.isfile( commit_file_path ):
			return self.log_error( 'Failed to find commit file {0}' . format( commit_file_path ) )

		return self.svn.commit( self.path, commit_file_path )

	def annotate( self, revision = None ):
		return self.svn.annotate( self.path, revision )

	def diff( self, revision_number = None, diff_tool = None ):
		return self.svn.diff( self.path, revision = revision_number, diff_tool = diff_tool )

	def add( self ):
		return self.svn.add( self.path )

	def log( self, xml = True, limit = None, revision = None ):
		return self.svn.log( self.path, xml = xml, limit = limit, revision = revision )

	def status( self, xml = True, quiet = False ):
		return self.svn.status( self.path, xml = xml, quiet = quiet )

	def update( self ):
		return self.svn.update( self.path )

	def cat( self, revision = None ):
		return self.svn.cat( self.path, revision = revision )

	def ls( self ):
		return self.svn.ls( self.path )

	def log_error( self, error ):
		self.__error = error

		if self.settings.log_errors():
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
