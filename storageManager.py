import os
import sys
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
            type_data = [encoded.decode()[:encoded.decode().find('\x00')] for encoded in unpacked[start_index:start_index + field_number + 1]]
            newType = Type(type_data)
            newPage.add_type(newType)
        return newPage

class TypeFile:

    def __init__(self):
        self.file_name = "sys.cat"

    def search_type(self, type_name):

        with open("sys.cat", "rb+") as sys_cat:

            index = 0
            while True:

                packed = sys_cat.read(TypePage.NUMBER_OF_BYTES)

                if len(packed) != 0:
                    curr_type_page = TypePage.unpack(packed)
                else:
                    return False

                if curr_type_page.search_type(type_name):
                    return True

                index += 1

        return False

    def add_type(self, type_data):

        new_type = Type(type_data)

        if self.search_type(type_data[0]):
            return

        with open("sys.cat", "rb+") as sys_cat:

            index = 0
            while True:

                packed = sys_cat.read(TypePage.NUMBER_OF_BYTES)

                if len(packed) != 0:
                    curr_type_page = TypePage.unpack(packed)
                else:
                    curr_type_page = TypePage()

                if curr_type_page.add_type(new_type):
                    packed = curr_type_page.pack()
                    position = index * TypePage.NUMBER_OF_BYTES
                    sys_cat.seek(position)
                    sys_cat.write(packed)
                    open(new_type.type_name + str(0) + ".txt", 'a').close()
                    break

                index += 1

    def delete_type(self, type_name):

        with open("sys.cat", "rb+") as sys_cat:

            index = 0
            while True:

                packed = sys_cat.read(TypePage.NUMBER_OF_BYTES)

                if len(packed) != 0:
                    curr_type_page = TypePage.unpack(packed)
                else:
                    break

                if curr_type_page.delete_type(type_name):
                    packed = curr_type_page.pack()
                    position = index * TypePage.NUMBER_OF_BYTES
                    sys_cat.seek(position)
                    sys_cat.write(packed)
                    break

                index += 1

        page_index = 0

        while os.path.exists(type_name + str(page_index) + ".txt"):
            os.remove(type_name + str(page_index) + ".txt")
            page_index += 1

    def list_types(self):

        types = []

        with open("sys.cat", "rb+") as sys_cat:

            index = 0
            while True:

                packed = sys_cat.read(TypePage.NUMBER_OF_BYTES)

                if len(packed) != 0:
                    curr_type_page = TypePage.unpack(packed)
                else:
                    break

                curr_types = curr_type_page.types
                types.extend([curr_type.type_name for curr_type in curr_types])

                index += 1

        return sorted(types)

class RecordFile:

    def __init__(self, record_type_name):
        self.file_name = record_type_name

    def search_record(self, type_name, record_key):

        page_index = 0

        while os.path.exists(type_name + str(page_index) + ".txt"):

            with open(type_name + str(page_index) + ".txt", "rb+") as record_file:

                index = 0
                while True:

                    packed = record_file.read(RecordPage.NUMBER_OF_BYTES)

                    if len(packed) != 0:
                        curr_record_page = RecordPage.unpack(packed)
                    else:
                        break

                    returned_record = curr_record_page.search_record(record_key)

                    if returned_record:
                        return returned_record.field_values

                    index += 1

                    if index == 1000:
                        break

            page_index += 1

        return None

    def create_record(self, type_name, field_values):

        if self.search_record(type_name, field_values[0]) is not None:
            self.delete_record(type_name, field_values[0])

        new_record = Record(field_values)

        page_index = 0

        while os.path.exists(type_name + str(page_index) + ".txt"):

            with open(type_name + str(page_index) + ".txt", "rb+") as record_file:

                index = 0

                while True:

                    packed = record_file.read(RecordPage.NUMBER_OF_BYTES)

                    if len(packed) != 0:
                        curr_type_page = RecordPage.unpack(packed)
                    else:
                        curr_type_page = RecordPage()

                    if curr_type_page.add_record(new_record):
                        packed = curr_type_page.pack()
                        position = index * RecordPage.NUMBER_OF_BYTES
                        record_file.seek(position)
                        record_file.write(packed)
                        return

                    index += 1

                    if index == 1000:
                        break

            page_index += 1
            open(type_name + str(page_index) + ".txt", "a").close()


    def update_record(self, type_name, record_key, field_values):

        new_record = Record(field_values)

        page_index = 0

        while os.path.exists(type_name + str(page_index) + ".txt"):

            with open(type_name + str(page_index) + ".txt", "rb+") as record_file:

                index = 0
                while True:

                    packed = record_file.read(RecordPage.NUMBER_OF_BYTES)

                    if len(packed) != 0:
                        curr_record_page = RecordPage.unpack(packed)
                    else:
                        break

                    returned_record = curr_record_page.search_record(record_key)

                    if returned_record:
                        curr_record_page.delete_record(record_key)
                        curr_record_page.add_record(new_record)
                        packed = curr_record_page.pack()
                        position = index * RecordPage.NUMBER_OF_BYTES
                        record_file.seek(position)
                        record_file.write(packed)
                        return

                    index += 1
                    if index == 1000:
                        break

            page_index += 1

    def delete_record(self, type_name, record_key):

        page_index = 0

        while os.path.exists(type_name + str(page_index) + ".txt"):

            with open(type_name + str(page_index) + ".txt", "rb+") as record_file:

                index = 0
                while True:

                    packed = record_file.read(RecordPage.NUMBER_OF_BYTES)

                    if len(packed) != 0:
                        curr_record_page = RecordPage.unpack(packed)
                    else:
                        break

                    returned_record = curr_record_page.search_record(record_key)

                    if returned_record:
                        curr_record_page.delete_record(record_key)
                        packed = curr_record_page.pack()
                        position = index * RecordPage.NUMBER_OF_BYTES
                        record_file.seek(position)
                        record_file.write(packed)
                        return

                    index += 1

                    if index == 1000:
                        break

            page_index += 1

    def list_records(self, type_name):

        records = []

        page_index = 0

        while os.path.exists(type_name + str(page_index) + ".txt"):

            with open(type_name + str(page_index) + ".txt", "rb+") as record_file:

                index = 0
                while True:

                    packed = record_file.read(RecordPage.NUMBER_OF_BYTES)

                    if len(packed) != 0:
                        curr_record_page = RecordPage.unpack(packed)
                    else:
                        break

                    curr_record_fields = [curr_record.field_values for curr_record in curr_record_page.records]

                    records.extend(curr_record_fields)

                    index += 1

                    if index == 1000:
                        break

            page_index += 1

        return sorted(records, key = lambda field_values: field_values[0])

        return records


input_file_name = sys.argv[1]
output_file_name = sys.argv[2]

open("sys.cat", "a").close()

with open(output_file_name, 'w') as output_file:
    with open(input_file_name, 'r') as input_file:

        for eachline in input_file:
            operation = eachline.strip().split()
            if not operation:
                continue
            action = operation[0]
            type = operation[1]

            if action != "list" or type != "type":
                type_name = operation[2]

            # DDL Operation
            if type == "type":

                type_file = TypeFile()

                # Create
                if action == "create":

                    field_number = operation[3]
                    field_names = operation[4:]

                    type_file.add_type([type_name] + field_names)

                # Delete
                elif action == "delete":

                    type_file.delete_type(type_name)

                # List
                else:
                    sorted_types = type_file.list_types()

                    for each_type in sorted_types:
                        output_file.write(each_type + '\n')

            # DML Operation
            else:

                record_file = RecordFile(type_name)

                if action != "create" and action != "list":
                    record_key = int(operation[3])

                # Create
                if action == "create":
                    field_values = [int(field_value) for field_value in operation[3:]]
                    record_file.create_record(type_name, field_values)

                # Delete
                elif action == "delete":
                    record_file.delete_record(type_name, record_key)

                # Update
                elif action == "update":
                    field_values = [int(field_value) for field_value in operation[3:]]
                    record_file.update_record(type_name, record_key, field_values)

                # Search
                elif action == "search":

                    field_values = record_file.search_record(type_name, record_key)
                    if field_values:
                        for i in range(len(field_values)):
                            output_file.write(str(field_values[i]))
                            if i != len(field_values) - 1:
                                output_file.write(' ')
                        output_file.write('\n')

                # List
                else:
                    sorted_records = record_file.list_records(type_name)
                    for each_record in sorted_records:
                        for i in range(len(each_record)):
                            output_file.write(str(each_record[i]))
                            if i != len(each_record) - 1:
                                output_file.write(' ')
                        output_file.write('\n')
