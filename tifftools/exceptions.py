class TifftoolsError(Exception):
    pass


class UnknownTagError(TifftoolsError):
    pass


class MustBeBigTiffError(TifftoolsError):
    pass


TifftoolsException = TifftoolsError
UnknownTagException = UnknownTagError
MustBeBigTiffException = MustBeBigTiffError
