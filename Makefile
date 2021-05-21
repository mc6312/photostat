packer = tar
pack = $(packer) caf
unpack = $(packer) --keep-newer-files -xaf
arcx = .tar.xz
todo = TODO
docs = COPYING Changelog README.md $(todo)
basename = photostat
srcversion = pstat_common
version = $(shell python3 -c 'from $(srcversion) import APP_VERSION; print(APP_VERSION)')
branch = $(shell git symbolic-ref --short HEAD)
title_version = $(shell python3 -c 'from $(srcversion) import APP_TITLE_VERSION; print(APP_TITLE_VERSION)')
zipname = $(basename).zip
arcname = $(basename)$(arcx)
srcarcname = $(basename)-$(branch)-src$(arcx)
pysrcs = *.py
srcs = $(pysrcs) *.ui *.svg
backupdir = ~/shareddocs/pgm/python/

app:
	zip $(zipname) $(srcs)
	@echo '#!/usr/bin/env python3' >$(basename)
	@cat $(zipname) >>$(basename)
	rm $(zipname)
	chmod 755 $(basename)

archive:
	make todo
	$(pack) $(srcarcname) $(srcs) Makefile *.geany $(docs)
distrib:
	make app
	make todo
	$(eval distname = $(basename)-$(version)$(arcx))
	$(pack) $(distname) $(basename) $(docs)
	mv $(distname) ~/downloads/
backup:
	make archive
	mv $(srcarcname) $(backupdir)
update:
	$(unpack) $(backupdir)$(srcarcname)
commit:
	make todo
	git commit -a -uno -m "$(version)"
docview:
	$(eval docname = README.htm)
	@echo "<html><head><meta charset="utf-8"><title>$(title_version) README</title></head><body>" >$(docname)
	markdown_py README.md >>$(docname)
	@echo "</body></html>" >>$(docname)
	x-www-browser $(docname)
	#rm $(docname)
show-branch:
	@echo "$(branch)"
todo:
	pytodo.py $(pysrcs) >$(todo)
