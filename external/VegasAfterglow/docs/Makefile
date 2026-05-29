# Makefile for Sphinx documentation

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = source
BUILDDIR      = build
DOXYGENDIR    = doxygen

# User-friendly check for sphinx-build
ifeq ($(shell which $(SPHINXBUILD) >/dev/null 2>&1; echo $$?), 1)
$(error The '$(SPHINXBUILD)' command was not found. Make sure you have Sphinx installed, or set the SPHINXBUILD environment variable to point to the full path of the '$(SPHINXBUILD)' executable.)
endif

.PHONY: help Makefile doxygen clean html all

# Generate help message with available targets
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@echo "  doxygen    to build Doxygen documentation"
	@echo "  all        to build both Doxygen and Sphinx documentation"

# Generate Doxygen documentation
doxygen:
	@mkdir -p $(DOXYGENDIR)
	@echo "Building Doxygen documentation..."
	@doxygen Doxyfile
	@echo "Done."

# Clean all build files
clean:
	@rm -rf $(BUILDDIR)/*
	@rm -rf $(DOXYGENDIR)/*
	@echo "Cleaned build directories."

# Build both Doxygen and Sphinx documentation
all: doxygen html

# Build only Sphinx HTML documentation
html:
	@$(SPHINXBUILD) -M html "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

# Catch-all target: route all unknown targets to Sphinx
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
