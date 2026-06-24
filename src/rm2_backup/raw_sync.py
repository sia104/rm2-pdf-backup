"""Read-only raw synchronisation from RM2 to Raspberry Pi storage.

Planned responsibilities:
- perform pre-flight checks;
- call rsync over SSH in read-only source mode;
- copy xochitl and template directories to raw/current;
- report sync status without modifying the RM2.
"""
