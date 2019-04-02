import struct

class Type:

    ENCODING = 'ascii'
    MAX_WORD_LENGTH = 8
    MAX_FIELD_NUMBER = 10
    FORMAT = '{}s'.format(MAX_WORD_LENGTH) * (MAX_FIELD_NUMBER + 1)

    def __init__(self, decoded = None):
        if decoded:
            self.type_name = decoded[0]
            self.field_names = decoded[1:]
        else:
            self.type_name = ''
            self.field_names = ['' for _ in range(Type.MAX_FIELD_NUMBER)]

    def pack(self):
        type_name_as_bytes = self.type_name.encode(Type.ENCODING)
        field_names_as_bytes = [field_name.encode(Type.ENCODING) for field_name in self.field_names]
        return struct.pack(Type.FORMAT, type_name_as_bytes, *field_names_as_bytes)

    @classmethod
    def unpack(cls, packed):
        unpacked = list(struct.unpack(Type.FORMAT, packed))
        decoded = [encoded.decode() for encoded in unpacked]
        return cls(decoded)

