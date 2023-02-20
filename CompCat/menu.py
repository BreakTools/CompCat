import CompCat

toolbar = nuke.menu('Nodes')
PluginMenu = toolbar.addMenu('CompCat', icon='CatIcon.png')
PluginMenu.addCommand('CompCat', 'CompCat.open_compcat_window()', icon='CatIcon.png')