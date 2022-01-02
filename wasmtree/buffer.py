import io
import struct


class Buffer:
    def __init__(self):
        self._buffer = io.BytesIO()

    def getvalue(self):
        return self._buffer.getvalue()

    def write_block_type(self, block_type):
        if block_type == 'empty':
            self.write_byte(0x40)
        elif isinstance(block_type, str):
            self.write_type(block_type)
        else:
            self._write_signed_integer(block_type)
        return self

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

    def write_data_count_section(self, data_count_section):
        if data_count_section and data_count_section.count is not None:
            stage = Buffer()
            stage.write_u32(data_count_section.count)
            self._write_staged_section(data_count_section.id, stage)
        return self

    def write_data_section(self, data_section):
        if data_section and data_section.segments:
            stage = Buffer()
            stage.write_u32(len(data_section.segments))

            for segment in data_section.segments:
                stage.write_byte(segment.id)
                if segment.id == 0x00:
                    self.write_expression(segment.offset)
                elif segment.id == 0x02:
                    self.write_u32(segment.index)
                    self.write_expression(segment.offset)
                self.write_u32(len(segment.contents))
                self.write_bytes(segment.contents)

            self._write_staged_section(data_section.id, stage)
        return self

    def write_element_section(self, element_section):
        if element_section and element_section.segments:
            stage = Buffer()
            stage.write_u32(len(element_section.segments))
            for segment in element_section.segments:
                stage.write_byte(segment.id)

                if segment.id == 0x00:
                    stage.write_expression(segment.offset)
                    stage.write_vec_u32(segment.function_indexes)

                elif segment.id == 0x01:
                    stage.write_byte(0x00)
                    stage.write_vec_u32(segment.function_indexes)

                elif segment.id == 0x02:
                    stage.write_u32(segment.table_index)
                    stage.write_expression(segment.offset)
                    stage.write_byte(0x00)
                    stage.write_vec_u32(segment.function_indexes)

                elif segment.id == 0x03:
                    stage.write_byte(0x00)
                    stage.write_vec_u32(segment.function_indexes)

                elif segment.id == 0x04:
                    stage.write_expression(segment.offset)
                    stage.write_vec_expression(segment.initializers)

                elif segment.id == 0x05:
                    stage.write_type(segment.type)
                    stage.write_vec_expression(segment.initializers)

                elif segment.id == 0x06:
                    stage.write_u32(segment.table_index)
                    stage.write_expression(segment.offset)
                    stage.write_type(segment.type)
                    stage.write_vec_expression(segment.intializers)

                elif segment.id == 0x07:
                    stage.write_type(segment.type)
                    stage.write_vec_expression(segment.intializers)

                else:
                    raise NotImplementedError(str(segment))

            self._write_staged_section(element_section.id, stage)
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
        return self

    def write_f32(self, value):
        self.write_bytes(struct.pack('<f', value))
        return self

    def write_f64(self, value):
        self.write_bytes(struct.pack('<d', value))
        return self

    def write_function_section(self, function_section):
        if function_section and function_section.type_indexes:
            stage = Buffer()
            stage.write_vec_u32(function_section.type_indexes)
            self._write_staged_section(function_section.id, stage)
        return self

    def write_global(self, glob):
        self.write_global_type(glob.type)
        self.write_expression(glob.expression)
        return self

    def write_global_section(self, global_section):
        if global_section and global_section.globals:
            stage = Buffer()
            stage.write_u32(len(global_section.globals))
            for glob in global_section.globals:
                self.write_global(glob)
            self._write_staged_section(global_section.id, stage)
        return self

    def write_global_type(self, global_type):
        self.write_type(global_type.type)
        modifiers = {'const': 0x00, 'var': 0x01}
        self.write_byte(modifiers[global_type.modifier])
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

    def write_import(self, imp):
        self.write_name(imp.module)
        self.write_name(imp.name)

        desc = imp.descriptor
        self.write_byte(desc.id)

        if desc.id == 0x00:
            self.write_u32(desc.type)

        elif desc.id == 0x01:
            self.write_table_type(desc.type)

        elif desc.id == 0x02:
            self.write_memory_type(desc.type)

        elif desc.id == 0x03:
            self.write_global_type(desc.type)

        else:
            raise NotImplementedError(str(imp))

        return self

    def write_import_section(self, import_section):
        if import_section and import_section.imports:
            stage = Buffer()
            for imp in import_section.imports:
                stage.write_import(imp)
            self._write_staged_section(import_section.id, stage)
        return self

    def write_instruction(self, instr):
        instr_id = instr.id
        self.write_byte(instr_id)

        if instr_id == 0x02 or instr_id == 0x03:
            self.write_block_type(instr.type)
            self.write_expression(instr.body)

        elif instr_id == 0x04:
            self.write_block_type(instr.type)
            if instr.else_case is None:
                self.write_expression(instr.true_case)
            else:
                for child in instr.true_case:
                    self.write_instruction(child)
                self.write_byte(0x05)
                self.write_expression(instr.else_case)

        elif instr_id == 0x0C or instr_id == 0x0D:
            self.write_u32(instr.label)

        elif instr_id == 0x0E:
            self.write_vec_u32(instr.labels)
            self.write_u32(instr.default)

        elif instr_id == 0x10:
            self.write_u32(instr.function)

        elif instr_id == 0x11:
            self.write_u32(instr.type_index)
            self.write_u32(instr.table_index)

        elif instr_id == 0xD0:
            self.write_type(instr.type)

        elif instr_id == 0xD1:
            self.write_u32(instr.function)

        elif instr_id == 0x1C:
            self.write_u32(len(intr.types))
            for type in intsr.types:
                self.write_type(type)

        elif 0x20 <= instr_id <= 0x26:
            self.write_u32(instr.index)

        elif 0x28 <= instr.id <= 0x3E:
            self.write_u32(instr.align)
            self.write_u32(inst.offset)

        elif instr.id == 0x3F or instr.id == 0x40:
            self.write_byte(instr.zero)

        elif instr_id == 0x41:
            self.write_i32(instr.number)

        elif instr_id == 0x42:
            self.write_i64(instr.number)

        elif instr_id == 0x43:
            self.write_f32(instr.number)

        elif instr_id == 0x44:
            self.write_f64(instr.number)

        elif instr_id == 0xFC:
            self.write_u32(intr.code)

            if instr.code == 0x08:
                self.write_u32(instr.data_index)
                self.wite_byte(instr.zero)

            elif instr.code == 0x09:
                self.write_u32(instr.data_index)

            elif instr.code == 0x0A:
                self.write_bytes(instr.zeros)

            elif instr.code == 0x0B:
                self.write_byte(instr.zero)

            elif instr.code == 0x0C:
                self.write_u32(instr.element)
                self.write_u32(instr.table)

            elif instr.code == 0x0D:
                self.write_u32(instr.element)

            elif instr.code == 0x0E:
                self.write_u32(instr.destination)
                self.write_u32(instr.source)

            elif 0x0F <= instr.code <= 0x11:
                self.write_u32(instr.table)

        return self

    def write_limits(self, limits):
        if hasattr(limits, 'max') and limits.max is not None:
            self.write_byte(0x01)
            self.write_u32(limits.min)
            self.write_u32(limits.max)
        else:
            self.write_byte(0x00)
            self.write_u32(limits.min)
        return self

    def write_memory_section(self, memory_section):
        if memory_section and memory_section.memory_types:
            stage = Buffer()
            stage.write_u32(len(memory_section.memory_types))
            for memory_type in memory_section.memory_types:
                stage.write_memory_type(memory_type)
            self._write_staged_section(memory_section.id, stage)
        return self

    def write_memory_type(self, memory_type):
        self.write_limits(memory_type.limits)
        return self

    def write_module(self, module):
        self.write_bytes(module.magic)
        self.write_bytes(module.version)
        self.write_custom_sections(module.custom1)

        self.write_type_section(module.type_section)
        self.write_custom_sections(module.custom2)

        self.write_import_section(module.import_section)
        self.write_custom_sections(module.custom3)

        self.write_function_section(module.function_section)
        self.write_custom_sections(module.custom4)

        self.write_table_section(module.table_section)
        self.write_custom_sections(module.custom5)

        self.write_memory_section(module.memory_section)
        self.write_custom_sections(module.custom6)

        self.write_global_section(module.global_section)
        self.write_custom_sections(module.custom7)

        self.write_export_section(module.export_section)
        self.write_custom_sections(module.custom8)

        self.write_start_section(module.start_section)
        self.write_custom_sections(module.custom9)

        self.write_element_section(module.element_section)
        self.write_custom_sections(module.custom10)

        self.write_data_count_section(module.data_count_section)
        self.write_custom_sections(module.custom11)

        self.write_code_section(module.code_section)
        self.write_custom_sections(module.custom12)

        self.write_data_section(module.data_section)
        self.write_custom_sections(module.custom13)
        return self

    def write_name(self, name):
        assert isinstance(name, str)
        bytes_str = name.encode('utf-8')
        self.write_u32(len(bytes_str))
        self.write_bytes(bytes_str)
        return self

    def write_start_section(self, start_section):
        if start_section:
            stage = Buffer()
            stage.write_u32(start_section.index)
            self._write_staged_section(start_section.id, stage)
        return self

    def write_table_section(self, table_section):
        if table_section and table_section.table_types:
            stage = Buffer()
            stage.write_u32(len(table_section.table_types))
            for table_type in table_section.table_types:
                stage.write_table_type(table_type)
            self._write_staged_section(table_section.id, stage)
        return self

    def write_table_type(self, table_type):
        self.write_type(table_type.type)
        self.write_limits(table_type.limits)
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

        if hasattr(type, 'parameter_types') and hasattr(type, 'result_types'):
            self.write_byte(0x60)

            self.write_u32(len(type.parameter_types))
            for param in type.parameter_types:
                self.write_type(param)

            self.write_u32(len(type.result_types))
            for result in type.result_types:
                self.write_type(result)

            return self

        raise NotImplementedError(str(type))

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

    def write_vec_expression(self, vec):
        self.write_u32(len(vec))
        for expr in vec:
            self.write_expression(expr)
        return self

    def write_vec_u32(self, vec):
        self.write_u32(len(vec))
        for u32 in vec:
            self.write_u32(u32)
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
