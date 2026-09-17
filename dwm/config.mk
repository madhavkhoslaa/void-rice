VERSION = 6.8-rice
PREFIX = $(HOME)/.local
MANPREFIX = ${PREFIX}/share/man
CC = cc
INCS = $(shell pkg-config --cflags x11 xft xinerama xext)
LIBS = $(shell pkg-config --libs x11 xft xinerama xext) -lfontconfig
CPPFLAGS = -D_DEFAULT_SOURCE -D_XOPEN_SOURCE=700L -DVERSION=\"${VERSION}\" -DXINERAMA
CFLAGS = -std=c99 -pedantic -Wall -Wno-unused-function -Wno-deprecated-declarations -Os ${INCS} ${CPPFLAGS}
LDFLAGS = ${LIBS}
