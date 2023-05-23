# Change Log

## Version 1.3.10

### Improvements
- Add some ImageJ tags found in a sample file ([#85](../../pull/85))

## Version 1.3.9

### Improvements
- Don't repeat bytes for immediately repeated byte series ([#82](../../pull/82))

## Version 1.3.8

### Improvements
- Add some aperio tags found in a sample file ([#81](../../pull/81))

## Version 1.3.7

### Improvements
- Ensure "tests" package is excluded from build ([#78](../../pull/78))

## Version 1.3.6

### Improvements
- Harden dumping invalid geokeys ([#77](../../pull/77))

## Version 1.3.5

### Improvements
- Guard against a missing tag set ([#74](../../pull/74))
 
## Version 1.3.4

### Improvements
- Improve yaml enum output ([#72](../../pull/72))

## Version 1.3.3

### Improvements
- Support writing IFDs before their associated data ([#71](../../pull/71))

## Version 1.3.2

### Improvements
- Add optional support for argcomplete ([#68](../../pull/68))
- Make it easier to add new ifds ([#70](../../pull/70))

## Version 1.3.1

### Improvements
- Support dumping to yaml ([#66](../../pull/66))
- Format GeoKey data for easier readability ([#67](../../pull/67))

## Version 1.3.0

### Features
- Better handle NDPI files ([#64](../../pull/64))

## Version 1.2.10

### Improvements
- Don't use pkg_resources for finding version ([#62](../../pull/62))

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
