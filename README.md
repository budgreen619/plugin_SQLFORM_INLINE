<h1>SQLFORM_INLINE</h1>

This is a web2py plugin leveraging the framework's ajax options to provide inline row editing functionality to the SQLFORM.grid method. It aims to provide the same features provided by web2py's SQLFORM.grid in addition to inline row editing. Because the inline edit feature loads a SQLFORM into the selected row, the plugin will work properly only if the grid includes fields from a single table.




<h2>Installation</h2>

Download the .w2p file and install it as a plugin via the web2py interface.

<h2>Update</h2>

Use the installation procedure above and overwrite the plugin content in your web2py app.

<h2>Usage</h2>
(1) Install the plugin.
(2) Create a separate controller for each inline grid.
(3) Load the inline grid controller into your page using the web2py LOAD helper.

<h2>Development Status</h2>

Although this plugin is intended to provide the same functionality offered by SQLFORM.grid, it is not yet fully tested and is currently in its initial stage of development. The CSS styling and jQuery table resizing, in particular, are still a little buggy.
If any of the options are not working properly, please feel free to let me know or, better yet, offer a proposed solution. I welcome any help or feedback to make this plugin as useful to the community as possible.


