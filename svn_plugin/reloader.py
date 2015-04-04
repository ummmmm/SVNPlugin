import sys
from imp import reload

reload_modules = []

for module in sys.modules:
	if module[ 0 : 9 ].lower() == 'svnplugin':
		reload_modules.append( module )

mod_prefix = 'SVNPlugin.svn_plugin'

module_load_order = [
	'',

	'.cache',
	'.settings',
	'.svn',
	'.repository',
	'.utils',
	'.thread_progress',

	'.threads.annotate_file',
	'.threads.diff_path',
	'.threads.log_path',
	'.threads.revision_file',
	'.threads.revision_list_load',
	'.threads.status_path',
	'.threads.update_path',
	'.threads',

	'.eventlisteners.on_activated',
	'.eventlisteners.on_post_save',
	'.eventlisteners',

	'.commands.svn_add',
	'.commands.svn_annotate',
	'.commands.svn_commit',
	'.commands.svn_diff',
	'.commands.svn_info',
	'.commands.svn_log',
	'.commands.svn_status',
	'.commands.svn_update',
	'.commands'
]

for suffix in module_load_order:
	module = mod_prefix + suffix

	if module in reload_modules:
		try:
			reload( sys.modules[ module ] )
		except ImportError:
			pass
