extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage',
              'sphinx.ext.graphviz', 'sphinx.ext.inheritance_diagram',
              'sphinx.ext.todo']
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'
project = u'dynpool'
copyright = u'2014-2015, Gustavo Picon'
version = '2.1'
release = '2.1'
exclude_trees = ['_build']
pygments_style = 'sphinx'
html_theme = 'default'
html_static_path = ['_static']
htmlhelp_basename = 'dynpooldoc'
latex_documents = [
    ('index', 'dynpool.tex', u'dynpool Documentation',
     u'Gustavo Picon', 'manual'),
]
