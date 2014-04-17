# Python agent notebooks #

This directory contains IPython notebooks covering a range of topics
related to the Python agent. These can describe processes for working on
the agent, the design of the agent, but also record the thought stream in
designing aspects of the agent, or evaluating the performance of some
aspect of the agent.

## Working with the notebooks ##

For each topic, create a separate sub directory where the name of the
directory is the topic for the notebook. A subdirectory is used so that
associated images and code files can be kept with the notebook.

In the subdirectory for the specific topic, now create the IPython notebook
with name 'notebook.ipynb'.

You can now work within the notebook, to add any documentation, code
examples, images etc.

When done and you are committing the notebook to the git repository, ensure
you generate a markdown version of the notebook and also add that to the
repository. This will mean that the notebook can be viewed from GHE without
anyone needing to use IPython itself.

You can convert the IPython notebook to markdown by running the command:

```
ipython nbconvert --to markdown notebook.ipynb
```

## Installing IPython itself ##

If on MacOS X, if you don't want to install IPython and all the
mathematical and charting packages yourselves that may want to use, then
install the free version of the Enthought distribution.

* https://www.enthought.com/products/epd/free/

When installing it, make sure you do not install it as your default Python
installation as you don't want it replacing the Apple version when working
with the agent.

Once installed, run the Enthought Canopy application and do an update of all
packages to ensure you get the newest IPython version.

When wish to start up the notebook server run:

```
~/Library/Enthought/Canopy_64bit/User/bin/ipython notebook
```

This should throw you into the web browser at which point you can navigate
to the point where you want to create the new notebook or select the
notebook to edit.
