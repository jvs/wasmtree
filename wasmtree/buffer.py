import io
import struct


class Buffer:
    def __init__(self):
        self._buffer = io.BytesIO()

    def getvalue(self):
        return self._buffer.getvalue()

    def write_byte(self, value):
        assert isinstance(value, int) and 0 <= value < 256
        self.write_bytes(value.to_bytes(1, byteorder='big'))
        return self

    def write_bytes(self, value):
        assert isinstance(value, bytes)
        self._buffer.write(value)
        return self

    def write_code_section(self, code_section):
        if code_section and code_section.entries:
            stage = Buffer()
            stage.write_u32(len(code_section.entries))
            for entry in code_section.entries:
                stage.write_code_entry(entry)
            self._write_staged_section(code_section.id, stage)
        return self

    def write_code_entry(self, entry):
        stage = Buffer()
        stage.write_u32(len(entry.locals))

        for locals in entry.locals:
            stage.write_u32(locals.count)
            stage.write_type(locals.type)

        stage.write_expression(entry.expression)
        staged_bytes = stage.getvalue()
        self.write_u32(len(staged_bytes))
        self.write_bytes(staged_bytes)
        return self

    def write_custom_sections(self, custom_sections):
        if custom_sections:
            for custom_section in custom_sections:
                self.write_custom_section(custom_section)
        return self

    def write_custom_section(self, custom_section):
        stage = Buffer()
        stage.write_name(custom_section.name)
        stage.write_bytes(custom_section.body)
        self._write_staged_section(custom_section.id, stage)
        return self

    def write_export(self, export):
        self.write_name(export.name)
        self.write_byte(export.descriptor.id)
        self.write_u32(export.descriptor.index)
        return self

    def write_export_section(self, export_section):
        if export_section and export_section.exports:
            stage = Buffer()
            stage.write_u32(len(export_section.exports))
            for export in export_section.exports:
                stage.write_export(export)
            self._write_staged_section(export_section.id, stage)
        return self

    def write_expression(self, expression):
        for instr in expression:
            self.write_instruction(instr)
        self.write_byte(0x0B)

    def write_f32(self, value):
        self.write_bytes(struct.pack('<f', value))
        return self

    def write_f64(self, value):
        self.write_bytes(struct.pack('<d', value))
        return self

    def write_function_section(self, function_section):
        if function_section and function_section.type_indexes:
            stage = Buffer()
            stage.write_u32(len(function_section.type_indexes))
            for index in function_section.type_indexes:
                stage.write_u32(index)
            self._write_staged_section(function_section.id, stage)
        return self

    def write_i32(self, value):
        assert isinstance(value, int)
        min_int = -1 * (2 ** 31)
        max_int = (2 ** 31) - 1
        assert min_int <= value <= max_int
        self._write_signed_integer(value)
        return self

    def write_i64(self, value):
        assert isinstance(value, int)
        min_int = -1 * (2 ** 63)
        max_int = (2 ** 63) - 1
        assert min_int <= value <= max_int
        self._write_signed_integer(value)
        return self

    def write_instruction(self, instr):
        instr_id = instr.id
        self.write_byte(instr_id)

        if instr_id == 0x20:
            self.write_u32(instr.index)

        elif instr_id == 0x41:
            self.write_i32(instr.number)

        return self

    def write_module(self, module):
        self.write_bytes(module.magic)
        self.write_bytes(module.version)
        self.write_custom_sections(module.custom1)
        self.write_type_section(module.type_section)
        self.write_custom_sections(module.custom2)
        # TODO: import_section
        self.write_function_section(module.function_section)
        self.write_custom_sections(module.custom4)
        # TODO: table_section, memory_section, global_section
        self.write_export_section(module.export_section)
        self.write_custom_sections(module.custom8)
        # TODO: start_section, element_section, data_count_section
        self.write_code_section(module.code_section)
        self.write_custom_sections(module.custom12)
        # TODO: data_seciont
        return self

    def write_name(self, name):
        assert isinstance(name, str)
        bytes_str = name.encode('utf-8')
        self.write_u32(len(bytes_str))
        self.write_bytes(bytes_str)
        return self

    def write_type(self, type):
        types = {
            'i32': 0x7F,
            'i64': 0x7E,
            'f32': 0x7D,
            'f64': 0x7C,
            'funcref': 0x70,
            'externref': 0x6F,
        }

        if isinstance(type, str):
            self.write_byte(types[type])
            return self

        if hasattr(type, 'params') and hasattr(type, 'results'):
            self.write_byte(0x60)

            self.write_u32(len(type.params))
            for param in type.params:
                self.write_type(param)

            self.write_u32(len(type.results))
            for result in type.results:
                self.write_type(result)

            return self

    def write_type_section(self, type_section):
        if type_section and type_section.function_types:
            stage = Buffer()
            stage.write_u32(len(type_section.function_types))
            for func_type in type_section.function_types:
                stage.write_type(func_type)
            self._write_staged_section(type_section.id, stage)
        return self

    def write_u32(self, value):
        assert isinstance(value, int)
        assert 0 <= value <= (2 ** 32)
        self._write_unsigned_integer(value)
        return self

    def _write_staged_section(self, section_id, buffer):
        contents = buffer.getvalue()
        self.write_byte(section_id)
        self.write_u32(len(contents))
        self.write_bytes(contents)
        return self

    def _write_signed_integer(self, value):
        assert isinstance(value, int)

        bottom_mask = 0xFF >> 1
        continue_flag = 1 << 7
        negative_flag = 1 << 6

        rest = value
        while True:
            byte = (rest & bottom_mask)
            is_negative = rest & negative_flag
            rest = rest >> 7
            is_done = rest == (-1 if is_negative else 0)
            flag = 0 if is_done else continue_flag
            self.write_byte(byte | flag)

            if is_done:
                return self

    def _write_unsigned_integer(self, value):
        assert isinstance(value, int) and value >= 0

        bottom_mask = 0xFF >> 1
        continue_flag = 1 << 7

        rest = value
        while True:
            byte = (rest & bottom_mask)
            rest = rest >> 7
            flag = continue_flag if rest else 0
            self.write_byte(byte | flag)

            if rest == 0:
                return self
