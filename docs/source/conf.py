import os
import sys
import shutil

sys.path.insert(0, os.path.abspath("../../"))

if os.path.exists("../../docs/build"):
    shutil.rmtree("../../docs/build")

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "miniopy-async"
copyright = "2022-%Y, L-ING"
author = "L-ING"
release = "1.21.2"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.duration",
    "sphinx.ext.extlinks",
    "sphinx.ext.githubpages",
    "sphinx.ext.viewcode",
]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"

extlinks = {
    "issue": (
        "https://github.com/hlf20010508/miniopy-async/issues/%s",
        "issue %s",
    ),  # :issue:`1` to link to issue 1
    "pr": (
        "https://github.com/hlf20010508/miniopy-async/pulls/%s",
        "pr %s",
    ),  # :pr:`1` to link to pr 1
    "discussion": (
        "https://github.com/hlf20010508/miniopy-async/discussions/%s",
        "discussion %s",
    ),  # :discussion:`1` to link to discussion 1
    "commit": (
        "https://github.com/hlf20010508/miniopy-async/commit/%s",
        "commit %s",
    ),  # :commit:`1` to link to commit 1
    "branch": (
        "https://github.com/hlf20010508/miniopy-async/tree/%s",
        "branch %s",
    ),  # :branch:`1` to link to branch 1
    "release": (
        "https://github.com/hlf20010508/miniopy-async/releases/tag/%s",
        "release %s",
    ),  # :release:`1` to link to release 1
}
