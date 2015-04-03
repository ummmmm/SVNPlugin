import sublime, sublime_plugin

import os
import xml.etree.ElementTree as ET

from ..cache						import Cache
from ..utils						import in_svn_root, find_svn_root, SvnPluginCommand
from ..settings 					import Settings
from ..repository 					import Repository
from ..thread_progress 				import ThreadProgress
from ..threads.revision_file 		import RevisionFileThread
from ..threads.annotate_file 		import AnnotateFileThread
from ..threads.revision_list_load 	import RevisionListLoadThread

class SvnPluginInfoCommand( sublime_plugin.WindowCommand, SvnPluginCommand ):
	def run( self, path = None ):
		if path is None:
			path = find_svn_root( self.get_file() )

			if path is None:
				return

		self.settings				= Settings()
		self.repository				= None
		self.commit_panel			= None
		self.previous				= []
		self.__error				= ''

		if os.path.isdir( path ):
			return self.directory_quick_panel( path )
		elif os.path.isfile( path ):
			return self.file_quick_panel( path )

	def directory_quick_panel( self, path ):
		self.repository = Repository( path )

		if not self.repository.ls():
			return sublime.error_message( self.repository.svn_error )

		try:
			root = ET.fromstring( self.repository.svn_output )
		except ET.ParseError:
			return self.log_error( 'Failed to parse XML' )

		entries = []

		for entry in root.getiterator( 'entry' ):
			kind = entry.get( 'kind' )

			entries.append( { 'kind': kind, 'path': os.path.join( path, entry.findtext( 'name' ) ) } )

		entries 			= sorted( entries, key = lambda k: k[ 'kind' ] )
		formatted_entries	= [ entry[ 'path' ] for entry in entries ]

		if self.previous:
			formatted_entries.insert( 0, '..' )

		self.show_quick_panel( formatted_entries, lambda index: self.directory_quick_panel_callback( entries, index ) )

	def directory_quick_panel_callback( self, entries, index ):
		if index == -1:
			return

		if self.previous and index == 0:
			path = self.previous.pop()
			return self.directory_quick_panel( path )

		offset 	= 0 if not self.previous else -1
		entry 	= entries[ index + offset ]

		self.previous.append( self.repository.path )

		if entry[ 'kind' ] == 'file':
			return self.file_quick_panel( entry[ 'path' ] )
		elif entry[ 'kind' ] == 'dir':
			return self.directory_quick_panel( entry[ 'path' ] )


	def file_quick_panel( self, file_path ):
		if self.repository is None or self.repository.path != file_path:
			self.repository = Repository( file_path )

		if not self.repository.is_tracked():
			top_level_file_entries = [ { 'code': 'af', 'value': 'Add File to Repository' } ]
		else:
			top_level_file_entries = [ { 'code': 'vr', 'value': 'Revisions' } ]

			if self.repository.is_modified():
				top_level_file_entries.extend( [ { 'code': 'cf', 'value': 'Commit' }, { 'code': 'rf', 'value': 'Revert' }, { 'code': 'df', 'value': 'Diff' } ] )

		formatted_entries = [ entry[ 'value' ] for entry in top_level_file_entries ]

		if self.previous:
			formatted_entries.insert( 0, '..' )

		self.show_quick_panel( formatted_entries, lambda index: self.file_quick_panel_callback( file_path, top_level_file_entries, index ) )

	def file_quick_panel_callback( self, file_path, entries, index ):
		if index == -1:
			return

		if self.previous and index == 0:
			path = self.previous.pop()
			return self.directory_quick_panel( path )

		offset	= 0 if not self.previous else -1
		code 	= entries[ index + offset ][ 'code' ]

		if code == 'af':
			return self.file_add()
		elif code == 'rf':
			return self.file_revert()
		elif code == 'vr':
			return self.file_revisions()
		elif code == 'cf':
			return self.file_commit()
		elif code == 'df':
			return self.file_diff()

	def file_add( self ):
		return self.window.run_command( 'svn_plugin_add', { 'path': self.repository.path } )

	def file_revert( self ):
		if not sublime.ok_cancel_dialog( 'Are you sure you want to revert file:\n\n{0}' . format( self.repository.path ), 'Yes, revert' ):
			return sublime.status_message( 'File not reverted' )

		if not self.repository.revert():
			return sublime.error_message( self.repository.error )

		return sublime.status_message( 'File reverted' )

	def file_commit( self ):
		return self.window.run_command( 'svn_plugin_commit', { 'path': self.repository.path } )

	def file_diff( self, revision = None ):
		return self.window.run_command( 'svn_plugin_diff', { 'path': self.repository.path, 'revision': revision } )

	def file_revisions( self ):
		thread = RevisionListLoadThread( self.repository, log_limit = self.settings.svn_log_limit(), revision = None, on_complete = self.file_revisions_callback )
		thread.start()
		ThreadProgress( thread, 'Loading revisions' )

	def file_revisions_callback( self, result ):
		if not result:
			return sublime.error_message( self.repository.error )

		try:
			root = ET.fromstring( self.repository.svn_output )
		except ET.ParseError:
			return self.log_error( 'Failed to parse XML' )

		revisions = []

		for child in root.getiterator( 'logentry' ):
			revisions.append( { 'number': child.get( 'revision', '' ), 'author': child.findtext( 'author', '' ), 'date': child.findtext( 'date', '' ), 'message': child.findtext( 'msg', '' ) } )

		self.revisions_quick_panel( revisions )

	def file_annotate( self, revision ):
		return self.window.run_command( 'svn_plugin_file_annotate', { 'path': self.repository.path, 'revision': revision } )

	def file_revision( self, revision ):
		thread = RevisionFileThread( self.repository, revision = revision, on_complete = self.file_revision_callback )
		thread.start()
		ThreadProgress( thread, 'Loading revision', 'Revision loaded' )

	def file_revision_callback( self, result ):
		if not result:
			return sublime.error_message( self.repository.error )

		current_syntax	= self.window.active_view().settings().get( 'syntax' )
		view 			= self.window.new_file()

		view.set_name( 'SVNPlugin: Revision' )
		view.set_syntax_file( current_syntax )
		view.set_scratch( True )
		view.run_command( 'append', { 'characters': self.repository.svn_output } )
		view.set_read_only( True )


	def revisions_quick_panel( self, revisions, selected_index = -1 ):
		revisions_formatted = [ [ '..' ] ]

		for revision in revisions:
			revisions_formatted.extend( [ 'r{0} | {1} | {2}' . format( revision[ 'number' ], revision[ 'author' ], revision[ 'date' ] ) ] )

		self.show_quick_panel( revisions_formatted, lambda index: self.revisions_quick_panel_callback( revisions, index ), lambda index: self.revision_highlight( revisions, index ), selected_index = selected_index )

	def revisions_quick_panel_callback( self, revisions, index ):
		self.hide_panel()

		if index == -1:
			return
		elif index == 0:
			return self.file_quick_panel( self.repository.path )

		offset				= 1
		revision_index 		= index - offset
		entries 			= [ { 'code': 'up', 'value': '..' }, { 'code': 'vf', 'value': 'View' }, { 'code': 'af', 'value': 'Annotate' } ]

		if revision_index != 0 or self.repository.is_modified(): # only show diff option if the current revision has been modified locally or it's an older revision
			entries.insert( 2, { 'code': 'df', 'value': 'Diff' } )

		self.show_quick_panel( [ entry[ 'value' ] for entry in entries ], lambda index: self.revision_action_callback( entries, revisions, revision_index, index ) )

	def revision_action_callback( self, entries, revisions, revision_index, index ):
		if index == -1:
			return

		code = entries[ index ][ 'code' ]

		if code == 'up':
			return self.revisions_quick_panel( revisions, selected_index = revision_index + 1 )

		revision = revisions[ revision_index ]

		if code == 'vf':
			return self.file_revision( revision = revision[ 'number' ] )
		elif code == 'df':
			return self.file_diff( revision = revision[ 'number' ] )
		elif code == 'af':
			return self.file_annotate( revision = revision[ 'number' ] )

	def revision_highlight( self, revisions, index ):
		if index == -1:
			return
		elif index == 0:
			return self.show_panel( None )

		offset 		= 1
		revision	= revisions[ index - offset ]

		self.show_panel( revision[ 'message' ] )

	def show_quick_panel( self, entries, on_select, on_highlight = None, selected_index = -1 ):
		sublime.set_timeout( lambda: self.window.show_quick_panel( entries, on_select, on_highlight = on_highlight, selected_index = selected_index ), 10 )

	def show_panel( self, content ):
		if self.settings.svn_log_panel():
			self.commit_panel = self.window.create_output_panel( 'svn_panel' )
			self.window.run_command( 'show_panel', { 'panel': 'output.svn_panel' } )
			self.commit_panel.set_read_only( False )
			self.commit_panel.run_command( 'append', { 'characters': content } )
			self.commit_panel.set_read_only( True )

	def hide_panel( self ):
		if self.commit_panel:
				self.window.run_command( 'hide_panel', { 'panel': 'output.svn_panel' } )
				self.commit_panel = None

	def log_error( self, error ):
		self.__error = error

		if self.settings.log_errors():
			print( error )

		return False

	@property
	def error( self ):
		return self.__error

class SvnPluginFileInfoCommand( SvnPluginInfoCommand ):
	def run( self ):
		if not in_svn_root( self.get_file() ):
			return

		self.window.run_command( 'svn_plugin_info', { 'path': self.get_file() } )

	def is_visible( self ):
		return in_svn_root( self.get_file() )

class SvnPluginFolderInfoCommand( SvnPluginInfoCommand ):
	def run( self ):
		if not in_svn_root( self.get_folder() ):
			return

		self.window.run_command( 'svn_plugin_info', { 'path': self.get_folder() } )

	def is_visible( self ):
		return in_svn_root( self.get_folder() )
