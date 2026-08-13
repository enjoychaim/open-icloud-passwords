# packaging for the Chrome Web Store.
# only runtime files are shipped; the allowlist lives in tools/pack.py.

VERSION := $(shell python3 -c "import json;print(json.load(open('manifest.json'))['version'])")
DIST    := dist
ZIP     := $(DIST)/open-icloud-passwords-$(VERSION).zip

.PHONY: pack pack-store clean list

# self-managed key: keep manifest "key" so the store ID stays pejdij... and native hosts keep working
pack:
	python3 tools/pack.py

# Google-managed key: strip manifest "key"; the store assigns a new ID (update install.sh EXT_ID after)
pack-store:
	python3 tools/pack.py --drop-key

# show exactly what the zip contains, without unpacking
list: pack
	unzip -l $(ZIP)

clean:
	rm -rf $(DIST)
