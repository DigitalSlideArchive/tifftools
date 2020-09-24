class TifftoolsException(Exception):
    pass


class UnknownTagException(TifftoolsException):
    pass


class MustBeBigTiffException(TifftoolsException):
    pass
