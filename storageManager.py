import struct

class Type:

    ENCODING = 'ascii'
    MAX_WORD_LENGTH = 8
    MAX_FIELD_NUMBER = 10
    EPSILON = b''
    FORMAT = 'q' + '{}s'.format(MAX_WORD_LENGTH) * (MAX_FIELD_NUMBER + 1)

    def __init__(self, type_data):
        self.type_name = type_data[0]
        self.field_names = type_data[1:]
        self.field_number = len(type_data) - 1

    def get_structured_type(self):
        structured_type = [self.field_number, self.type_name.encode(Type.ENCODING)]
        structured_type.extend([field_name.encode(Type.ENCODING) for field_name in self.field_names])
        structured_type.extend([Type.EPSILON for _ in range(Type.MAX_FIELD_NUMBER - len(self.field_names))])
        return structured_type

    def pack(self):
        return struct.pack(Type.FORMAT, *self.get_structured_type())

    @classmethod
    def unpack(cls, packed):
        unpacked = list(struct.unpack(Type.FORMAT, packed))
        field_number = unpacked.pop(0)
        decoded = [encoded.decode() for encoded in unpacked]
        return cls(decoded[:field_number+1])

class Record:

    MAX_FIELD_NUMBER = 10
    FORMAT = '?' + ('q' * (MAX_FIELD_NUMBER + 2))

    def __init__(self, field_values, is_valid = True):
        self.is_valid = is_valid
        self.key = field_values[0]
        self.field_number = len(field_values)
        self.field_values = field_values

    def get_structured_record(self):
        structured_record = [self.is_valid, self.key, self.field_number]
        for field_value in self.field_values:
            structured_record.append(field_value)
        for _ in range(Record.MAX_FIELD_NUMBER - self.field_number):
            structured_record.append(0)
        return structured_record

    def pack(self):
        return struct.pack(Record.FORMAT, *self.get_structured_record())

    @classmethod
    def unpack(cls, packed):
        unpacked = list(struct.unpack(Record.FORMAT, packed))
        return cls(unpacked[3:], unpacked[0])

class RecordPage:

    MAX_RECORD_NUMBER = 30
    NUMBER_OF_BYTES = 3128
    FORMAT = 'q' + Record.FORMAT * MAX_RECORD_NUMBER
    STRUCTURED_EMPTY_RECORD = Record([0], False).get_structured_record()

    def __init__(self):
        self.number_of_records = 0
        self.records = []

    def add_record(self, record):
        if self.number_of_records < 30:
            self.number_of_records += 1
            self.records.append(record)
            return True
        return False

    def search_record(self, record_key):
        if self.number_of_records > 0:
            for record in self.records:
                if record.key == record_key:
                    return record
        return None

    def delete_record(self, record_key):
        record = self.search_record(record_key)
        if record:
            self.records.remove(record)
            self.number_of_records -= 1
            return True
        return False

    def pack(self):
        structured_page = [self.number_of_records]
        for record in self.records:
            structured_page.extend(record.get_structured_record())
        for _ in range(RecordPage.MAX_RECORD_NUMBER - self.number_of_records):
            structured_page.extend(RecordPage.STRUCTURED_EMPTY_RECORD)
        return struct.pack(RecordPage.FORMAT, *structured_page)

    @classmethod
    def unpack(cls, packed):
        unpacked = list(struct.unpack(RecordPage.FORMAT, packed))
        newPage = cls()
        number_of_records = unpacked[0]
        for index in range(number_of_records):
            start_index = index * 13 + 4
            end_index = start_index + unpacked[start_index - 1]
            newRecord = Record(unpacked[start_index:end_index])
            newPage.add_record(newRecord)
        return newPage


class TypePage:

    MAX_TYPE_NUMBER = 30
    NUMBER_OF_BYTES = 2888
    FORMAT = 'q' + Type.FORMAT * MAX_TYPE_NUMBER
    STRUCTURED_EMPTY_TYPE = Type(["NONE"]).get_structured_type()

    def __init__(self):
        self.number_of_types = 0
        self.types = []

    def add_type(self,type):
        if self.number_of_types < 30:
            self.types.append(type)
            self.number_of_types += 1
            return True
        return False

    def search_type(self, type_name):
        if self.number_of_types > 0:
            for type in self.types:
                if type.type_name == type_name:
                    return type

        return None

    def delete_type(self, type_name):
        type = self.search_type(type_name)
        if type:
            self.types.remove(type)
            self.number_of_types -= 1
            return True
        return False

    def pack(self):
        structured_page = [self.number_of_types]
        for type in self.types:
            structured_page.extend(type.get_structured_type())
        for _ in range(TypePage.MAX_TYPE_NUMBER - self.number_of_types):
            structured_page.extend(TypePage.STRUCTURED_EMPTY_TYPE)
        return struct.pack(TypePage.FORMAT, *structured_page)

    @classmethod
    def unpack(cls, packed):
        unpacked = list(struct.unpack(TypePage.FORMAT, packed))
        newPage = cls()
        number_of_types = unpacked[0]
        for index in range(number_of_types):
            start_index = index * 12 + 2
            field_number = unpacked[start_index-1]
            type_data = [encoded.decode() for encoded in unpacked[start_index:start_index + field_number + 1]]
            newType = Type(type_data)
            newPage.add_type(newType)
        return newPage