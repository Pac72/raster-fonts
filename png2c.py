#!/usr/bin/env python3
import sys
import png
import argparse

# if len(sys.argv) < 2:
#     sys.stderr.write("Please specify the input PNG file\n")
#     sys.exit(1)

parser = argparse.ArgumentParser(description='Convert PNG font image to a C array.')

parser.add_argument('filename', metavar='png_filepath', type=str,
                    help='Input PNG image with a bitmap of an 8x8 matrix of 256 adjacent characters')
parser.add_argument('-c', '--columns', action='store_true',
                    help='Produce the columns of the chars instead of their rows')

args = parser.parse_args()

reader = png.Reader(filename=args.filename)
data = reader.asRGB()
size = data[:2] # get image width and height
char_width = int(size[0] / 16)
char_height = int(size[1] / 16)
char_size = (char_width, char_height) # 16 characters in a row, 16 rows of characters
bitmap = list(data[2]) # get image RGB values

rowcolmode = "column" if args.columns else "row"

sys.stdout.write("""#include "font.h"

#if 0
#ifndef FONT_H_
#define FONT_H_

typedef struct {
    unsigned char_width;
    unsigned char_height;
    const char * font_name;
    unsigned char first_char;
    unsigned char last_char;
    unsigned char * font_bitmap;
} font_t;

extern const font_t console_fonts[];

#endif /* FONT_H_ */
#endif

/* %s mode: the array contains the %ss of the chars */

""" % (rowcolmode, rowcolmode))

sys.stdout.write("""unsigned char console_font_%dx%d[] = {
""" % char_size)

raster = []
for line in bitmap:
    raster.append([c == 255 and 1 or 0 for c in [line[k+1] for k in range(0, size[0] * 3, 3)]])

# array of character bitmaps; each bitmap is an array of lines, each line
# consists of 1 - bit is set and 0 - bit is not set
char_bitmaps = [] 
for c in range(256): # for each character
    char_bitmap = []
    raster_row = int(int(c / 16) * char_height)
    offset = int(int(c % 16) * char_width)
    if args.columns:
        for x in range(char_width): # for each column of the character
            char_col = []
            for y in range(char_height - 1, -1, -1):
                char_col.append(raster[raster_row + y][offset + x])
            char_bitmap.append(char_col)
    else:
        for y in range(char_height): # for each scan line of the character
            rr = raster_row + y
            char_bitmap.append(raster[rr][offset : offset + char_width])
    char_bitmaps.append(char_bitmap)
raster = None # no longer required

# how many bytes a single character scan line should be
num_bytes_per_scanline = int(int(char_width + 7) / 8)

# convert the whole bitmap into an array of character bitmaps
char_bitmaps_processed = []
for c in range(len(char_bitmaps)):
    bitmap = char_bitmaps[c]
    encoded_lines = []
    for line in bitmap:
        encoded_line = []
        for b in range(num_bytes_per_scanline):
            offset = b * 8
            char_byte = 0
            mask = 0x80
            for x in range(8):
                if b * 8 + x >= char_width:
                    break
                if line[offset + x]:
                    char_byte += mask
                mask >>= 1
            encoded_line.append(char_byte)
        encoded_lines.append([encoded_line, line])
    char_bitmaps_processed.append([c, encoded_lines])
char_bitmaps = None

def _ctoi(c):
    if type(c) == type(""):
        return ord(c)
    else:
        return c

def printable_char(ch):
    ich = _ctoi(ch)
    if 32 <= ich <= 126:
        if ich == 34:
            return "\\\""
        else:
            return chr(ich)
    return "\\{value:03o}".format(value=ich)

for c in char_bitmaps_processed:
    ch = c[0]
    sys.stdout.write("""
    /*
     * code=%d, hex=0x%02X, ascii="%s"
     */
""" % (ch, ch, printable_char(ch)))
    for line in c[1]:
        sys.stdout.write("    ")
        for char_byte in line[0]:
            sys.stdout.write(("0x%02X," % char_byte))
        sys.stdout.write("  /* %s */" % ''.join([str(s) for s in line[1]]))
        sys.stdout.write("\n")

sys.stdout.write("""};

""")
