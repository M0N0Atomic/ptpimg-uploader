===============
ptpimg_uploader
===============


Take screenshots and upload image file or image URL to the ptpimg.me image hosting.


Installation
------------

  * Install python3 package ``requests`` (usually ``apt-get install python3-requests`` or ``pip3 install requests``).

  * If you want to take screenshots ``ffmpeg`` is needed in path or in the current working directory.
  
  * For mediainfo capability, install python3 package ``pymediainfo`` (usually ``apt-get install pymediainfo`` or ``pip3 install pymediainfo``).
  
  * If you want clipboard support, install ``pyperclip`` too.


API key
-------

To find your PTPImg API key, login to https://ptpimg.me, open the page source
(i.e. "View->Developer->View source" menu in Chrome), find the string api_key
and copy the hexademical string from the value attribute. Your API key should
look like 43fe0fee-f935-4084-8a38-3e632b0be68c.

You can export your ptpimg.me API key (usually in .bashrc or .zshenv) using:

.. code-block:: bash

    export PTPIMG_API_KEY=<your hex key>


or use the ``-k`` / ``--api-key`` command-line switch.

How to use
----------

Run

.. code-block:: bash

    ptpimg_uploader.py -h


to get command-line help.

Usage:

.. code-block:: bash

    ptpimg_uploader.py -k API_KEY


An uploaded URL will be printed to the console.

If ``--media`` parameter is specified, mediainfo will be printed along with tags:

.. code-block:: bash

    ptpimg_uploader.py --media

If ``--bbcode`` parameter is specified, URLS will be wrapped in BBCode ``[img]`` tags:

.. code-block:: bash

    ptpimg_uploader.py --bbcode


If pyperclip python package is installed, the URL will be additionally copied to the clipboard.

If output is a terminal, a bell will be ringed on completion (can be disabled with a ``--nobell`` parameter).

The resulting output is printed, and copied to your clipboard with newlines in between.

License
-------

BSD

Acknowledgments
---------------

* mjpieters - a great refactoring and Python packaging
* lukacoufyl - fixing image upload order
