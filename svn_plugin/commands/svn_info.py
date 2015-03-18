import sublime, sublime_plugin
import os

from ..svn import SVN
from ..settings import Settings
from ..thread_progress import ThreadProgress
from ..threads.revision_file import RevisionFileThread
from ..threads.annotate_file import AnnotateFileThread
from ..threads.revision_list_load import RevisionListLoadThread

NOT_SVN_DIRECTORY	= 'Directory is not a listed SVN repository'
NOT_SVN_FILE		= 'File is not in a listed SVN repository'

class SvnInfoCommand( sublime_plugin.WindowCommand ):
	def run( self, file = False, directory = False ):
		if ( file == directory ):
			return

		self.svn					= SVN()
		self.settings				= Settings()
		self.file_path				= self.window.active_view().file_name()
		self.commit_panel			= None
		self.validate_file_paths	= set()

		if not self.svn.valid:
			return

		if directory:
			return self.info_directory_quick_panel()

		return self.info_file_quick_panel( self.file_path )


	def info_directory_quick_panel( self ):
		self.show_quick_panel( self.svn.directories, self.info_directory_callback )

	def info_directory_callback( self, index ):
		if index == -1:
			return

		directory = self.svn.directories[ index ]

		directory_entries = [ { 'code': 'up', 'value': '..' }, { 'code': 'vf', 'value': 'View Files' }, { 'code': 'vr', 'value': 'View Revisions' } ]

		if self.svn.is_modified( directory ):
			directory_entries.insert( 2, { 'code': 'mf', 'value': 'View Modified Files' } )

		self.show_quick_panel( [ entry[ 'value' ] for entry in directory_entries ], lambda index: self.directory_action_callback( directory_entries, index ) )

	def directory_action_callback( self, directory_entries, index ):
		if index == -1:
			return
		elif index == 0:
			return self.info_directory_quick_panel()


	def info_file_quick_panel( self, file_path ):
		if file_path not in self.validate_file_paths:
			if not self.svn.in_svn_directory( self.file_path ):
				sublime.error_message( NOT_SVN_FILE )
				return

			self.validate_file_paths.add( file_path )

		if not self.svn.is_tracked( file_path ):
			top_level_file_entries = [ { 'code': 'af', 'value': 'Add File to Repository' } ]
		else:
			top_level_file_entries = [ { 'code': 'vr', 'value': 'Revisions' } ]

			if self.svn.is_modified( file_path ):
				top_level_file_entries.extend( [ { 'code': 'cf', 'value': 'Commit' }, { 'code': 'rf', 'value': 'Revert' }, { 'code': 'df', 'value': 'Diff' } ] )

		self.show_quick_panel( [ entry[ 'value' ] for entry in top_level_file_entries ], lambda index: self.info_file_callback( file_path, top_level_file_entries, index ) )

	def info_file_callback( self, file_path, entries, index ):
		if index == -1:
			return

		offset	= 0
		code 	= entries[ index - offset ][ 'code' ]

		if code == 'af':
			return self.svn.add_file( file_path )
		elif code == 'vr':
			return self.revisionlist_load( file_path )
		elif code == 'cf':
			return self.window.run_command( 'svn_commit', { 'file_path': file_path } )
		elif code == 'rf':
			return self.svn.revert_file( file_path )
		elif code == 'df':
			return self.window.run_command( 'svn_diff', { 'file_path': file_path } )

	def revisionlist_load( self, file_path ):
		thread = RevisionListLoadThread( self.svn, self.settings, file_path, self.revisions_quick_panel )
		thread.start()
		ThreadProgress( thread, 'Loading revisions' )

	def revisions_quick_panel( self, file_path, revisions, selected_index = -1 ):
		revisions_formatted = [ [ '..' ] ]

		for revision in revisions:
			revisions_formatted.extend( [ self.revision_format( revision ) ] )

		self.show_quick_panel( revisions_formatted, lambda index: self.revision_callback_quick_panel( file_path, revisions, index ), lambda index: self.revision_highlight( revisions, index ), selected_index = selected_index )

	def revision_callback_quick_panel( self, file_path, revisions, index ):
		self.hide_panel()

		if index == -1:
			return
		elif index == 0:
			return self.info_file_quick_panel( file_path )

		offset				= 1
		revision_index 		= index - offset
		entries 			= [ { 'code': 'up', 'value': '..' }, { 'code': 'vf', 'value': 'View' }, { 'code': 'af', 'value': 'Annotate' } ]

		if revision_index != 0 or self.svn.is_modified( file_path ): # only show diff option if the current revision has been modified locally or it's an older revision
			entries.insert( 2, { 'code': 'df', 'value': 'Diff' } )

		self.show_quick_panel( [ entry[ 'value' ] for entry in entries ], lambda index: self.revision_action_callback( file_path, entries, revisions, revision_index, index ) )

	def revision_action_callback( self, file_path, entries, revisions, revision_index, index ):
		if index == -1:
			return

		code = entries[ index ][ 'code' ]

		if code == 'up':
			return self.revisions_quick_panel( file_path, revisions, selected_index = revision_index + 1 )

		revision = revisions[ revision_index ]

		if code == 'vf':
			return self.view_revision( revision[ 'path' ], revision[ 'number' ] )
		elif code == 'df':
			return self.diff_revision( revision[ 'path' ], revision[ 'number' ] )
		elif code == 'af':
			return self.annotate_revision( revision[ 'path' ], revision[ 'number' ] )

	def revision_highlight( self, revisions, index ):
		if index == -1:
			return
		elif index == 0:
			return self.show_panel( None )

		offset 		= 1
		revision	= revisions[ index - offset ]

		self.show_panel( revision[ 'message' ] )

	def revision_format( self, revision ):
		return 'r{0} | {1} | {2}' . format( revision[ 'number' ], revision[ 'author' ], revision[ 'date' ] )


	def diff_revision( self, file_path, number ):
		self.window.run_command( 'svn_diff', { 'file_path' : file_path, 'revision' : number } )

	def annotate_revision( self, file_path, number ):
		thread = AnnotateFileThread( self.svn, file_path, number, self.annotate_callback )
		thread.start()
		ThreadProgress( thread, 'Loading annotation of {0}' . format( file_path ) )

	def annotate_callback( self, file_path, number, content ):
		self.revision_or_annotate_output( 'a', file_path, number, content )

	def view_revision( self, file_path, number ):
		thread = RevisionFileThread( self.svn, file_path, number, self.revision_callback )
		thread.start()
		ThreadProgress( thread, 'Loading revision of {0}' . format( file_path ) )

	def revision_callback( self, file_path, number, content ):
		self.revision_or_annotate_output( 'r', file_path, number, content )

	def revision_or_annotate_output( self, r_or_a, file_path, number, content ):
		temp_directory	= self.settings.svn_revisions_temp_directory()
		current_syntax	= self.window.active_view().settings().get( 'syntax' )

		if temp_directory is not None and os.path.isdir( temp_directory ) and os.access( temp_directory, os.W_OK ):
			try:
				temp_file = os.path.join( temp_directory, 'r{0}-{1}-{2}' . format( number, r_or_a, os.path.basename( file_path ) ) )

				with open( temp_file, 'w+' ) as fh:
					fh.write( content )

				view = self.window.open_file( temp_file )
				view.set_syntax_file( current_syntax )
			except:
				svn_plugin.log_error( "Failed to create temp revision file '{0}'" . format( temp_file ) )
		else:
			view = self.window.new_file()
			view.run_command( 'append', { 'characters': content } )
			view.set_syntax_file( current_syntax )

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
