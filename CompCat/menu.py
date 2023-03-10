toolbar = nuke.menu('Nodes')
compcat_menu = toolbar.addMenu('CompCat', icon='CatIcon.png')
compcat_menu.addCommand('CompCat', 'import comp_cat;comp_cat.open_compcat_window()', icon='CatIcon.png')