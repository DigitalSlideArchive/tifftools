import os

import pooch

registry = {
    # Aperio file with JP2K compression.
    # Source: TCGA-CV-7242-11A-01-TS1.1838afb1-9eee-4a70-9ae3-50e3ab45e242.svs
    'aperio_jp2k.svs': 'sha512:9a4312bc720e81ef4496cc33c71c122b82226f72bc4944b0192cc83a93b9ed7f69612d3f4369279c2ec41183e3f684cca7e068208b7d0a42bdca26cbdc3b9aac',  # noqa
    # Hamamatsu file
    # Source: OS-2.ndpi
    'hamamatsu.ndpi': 'sha512:f788288ed1f8ab55a05d33f218fd4bafbc59e3ecc2ade40b5127b53caaaaaf3c8c9ba42d022082c27b673e1ee6dd433eb21a1d57edf4e6694dcd7eea89778941',  # noqa
    # Philips file
    # Source: sample_image.ptif
    'philips.ptif': 'sha512:ec0ec688537080e4ec2abb3978c14577df87250a2c0af42beaadc8f00f0baba210997d5d2fe7cfeeceb841885b6adad0c9f607e35eddcc479eb487bd3c1e28ac',  # noqa
    # OME TIFF with SubIFDs
    'sample.subifd.ome.tif': 'sha512:35ec252c94b1ad0b9d5bd42c89c1d15c83065d6734100d6f596237ff36e8d4495bcfed2c9ea24ab0b4a35aef59871da429dbd48faf0232219dc4391215ba59ce',  # noqa
    # Tiff with secondary image, EXIF, and GPS IFDs
    'd043-200.tif': 'sha512:0ce72614df0409297c2a7261d13fd2501fcc4a7044680f1de00c1c21620a2bcc233a7ca5cf92e704d7364c6a8bb79e12d2122063b1f4ccce09b550525ba728ab',  # noqa
    # Tiff with subifds with subifds
    'subsubifds.tif': 'sha512:372ca32735c8a8fdbe2286dabead9e779da63f10ba81eda84625e5273f76d74ca1a47a978f67e9c00c12f7f72009c7b2c07a641e643bb0c463812f4ae7f15d6e',  # noqa
    # Tiff with GeoKey data
    'landcover_sample_1000.tif': 'sha512:0a1e8c4cf29174b19ddece9a2deb7230a31e819ee78b5ec264feda6356abf60d63763106f1ddad9dd04106d383fd0867bf2db55be0552c30f38ffb530bf72dec',  # noqa
}


class DKCPooch(pooch.Pooch):
    def get_url(self, fname):
        self._assert_file_in_registry(fname)
        algo, hashvalue = self.registry[fname].split(':')
        return self.base_url.format(algo=algo, hashvalue=hashvalue)


datastore = DKCPooch(
    path=pooch.utils.cache_location(
        os.path.join(os.environ.get('TOX_WORK_DIR', pooch.utils.os_cache('pooch')), 'dkc_datastore')
    ),
    base_url='https://data.kitware.com/api/v1/file/hashsum/{algo}/{hashvalue}/download',
    registry=registry,
)
