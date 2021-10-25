# Change Log

## Version 1.2.9

### Improvements
- Speed up constants class ([#60](../../pull/60))

## Version 1.2.8

### Improvements
- When creating some tags, return a TiffTag rather than TiffConstant ([#57](../../pull/57))
- Added new JPEGXL compression tag ([#58](../../pull/58))

## Version 1.2.7

### Improvements
- Rename Exceptions to Errors ([#56](../../pull/56))

## Version 1.2.6

### Improvements
- Align IFD values word boundaries ([#54](../../pull/54))
- Output small tiffs in more cases ([#53](../../pull/53))

## Version 1.2.5

### Improvements
- IFDs are output on word boundaries ([#52](../../pull/52))

## Version 1.2.4

### Bug fixes
- Fix checking offsets in merging multiple files ([#49](../../pull/49))

## Version 1.2.3

### Improvements
- More constants ([#48](../../pull/48))

## Version 1.2.2

### Bug fixes
- Better handle invalid unicode ([#46](../../pull/46))

## Version 1.2.1

### Improvements
- More tags ([#42](../../pull/42))

### Bug fixes
- Better detect the need to write bigtiff files ([#45](../../pull/45))

## Version 1.2.0

### Improvements
- Bitfields are now specified with a mask and are dumped more clearly ([#38](../../pull/38))
- Compression methods are now marked if they are usually lossy ([#39](../../pull/39))
- Report an estimated quality when dumping the JPEGTables tag ([#40](../../pull/40))

## Version 1.1.1

### Improvements
- Grouped reads for faster file generation ([#37](../../pull/37))

## Version 1.1.0

### Improvements
- More tags, including more GeoTIFF tags ([#33](../../pull/33))
- tifftools dump can show information on multiple files ([#35](../../pull/35))
- Help reports the version number ([#34](../../pull/34))

### Changes
- tifftools concat now takes sources before the destination ([#35](../../pull/35))

## Version 1.0.0

First release.
