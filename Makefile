packer = 7z
pack = $(packer) a -mx=9
arcx = .7z
docs = COPYING README.md
resources = photostat.svg
sources = __main__.py photostat.py psabout.py pscommon.py psconfig.py psgtktools.py psstat.py
basename = photostat
ziparcname = $(basename).zip
arcname = $(basename)$(arcx)
srcarcname = $(basename)-src$(arcx)
backupdir = ~/shareddocs/pgm/python/

app:
	$(pack) -tzip $(ziparcname) $(sources)
	@echo '#!/usr/bin/env python3' >$(basename)
	@cat $(ziparcname) >> $(basename)
	chmod 755 $(basename)
	rm $(ziparcname)
distrib:
	make app
	$(pack) $(arcname) $(basename) $(resources) $(docs)
src-archive:
	$(pack) $(srcarcname) *.py *.svg *. Makefile *.geany $(docs)
backup:
	make src-archive
	mv $(srcarcname) $(backupdir)
update:
	$(packer) x -y $(backupdir)$(srcarcname)

