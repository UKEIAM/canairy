"""Shared client for the luftmessnetz API (Hamburg, Berlin).

Both networks run the same software and expose identical endpoints. The
public packages `canairy.hh` and `canairy.be` only set the base URL and
re-export the models under network-prefixed names.
"""
