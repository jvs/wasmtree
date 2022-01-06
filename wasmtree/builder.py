import itertools

from . import buffer, parser


class Builder:
    number_types = ['i32', 'i64', 'f32', 'f64']
    reference_types = ['funcref', 'externref']
    value_types = number_types + reference_types

    def __init__(self):
        self.function_types = []
        self.function_types_map = {}
        self.leading_custom_sections = []
        self.trailing_custom_sections = []
        self.imports = []
        self.function_annotations = []
        self.function_bodies = []
        self.tables = []
        self.memories = []
        self.globals = []
        self.exports = []
        self.start_function_index = None
        self.function_element_indexes = []
        self.data_segments = []

    def add_block_type(self, block_type):
        if isinstance(block_type, str):
            if block_type == 'empty' or block_type in self.value_types:
                return block_type

        if isinstance(block_type, (list, tuple)) and len(block_type) == 2:
            function_type = self.function_type(*block_type)
            return self.add_function_type(function_type)

        raise ValueError(
            "Expected 'empty' or value type or function type."
            f' Received: {block_type!r}.'
        )

    def add_custom_section(self, name, body, position='end'):
        if not isinstance(name, str):
            raise TypeError(f'Expected name to be a str. Received: {name!r}')

        if not isinstance(body, bytes):
            raise TypeError(
                f'Expected body to be a bytes object. Received: {type(body)}.'
            )

        if position not in ['start', 'end']:
            raise ValueError("Expected position to be either 'start' or 'end'.")

        dst = (self.trailing_custom_sections
            if position == 'end'
            else self.leading_custom_sections)

        dst.append(parser.CustomSection(name=name, body=body))

    def add_data_segment(self, offset, bytestr):
        if not isinstance(bytestr, bytes):
            raise TypeError(
                'Data segment must be a bytes ojecct.'
                f' Received: {type(bytestr)}.'
            )

        self.data_segments.append(parser.DefaultDataSegment(offset, bytestr))

    def add_function(
            self,
            parameter_types,
            result_types,
            local_types,
            expression=None,
            export_as=None,
            add_to_table=False,
            is_start_function=False,
        ):
        function_type = self.function_type(parameter_types, result_types)
        self.add_function_type(function_type)
        type_index = self.function_type_index(function_type)

        locals = []
        for t in local_types:
            t = self.value_type(t)
            if locals and locals[-1].type == t:
                locals[-1].count += 1
            else:
                locals.append(parser.Locals(count=1, type=t))

        if expression is None:
            expression = []

        expression = self.expression(expression)
        entry = parser.CodeEntry(locals, expression)
        function_index = len(self.function_bodies)
        self.function_annotations.append(type_index)
        self.function_bodies.append(entry)

        export_as = self._export_as(export_as)
        if export_as is not None:
            self.export_function(export_as, function_index)

        if is_start_function:
            self.start_function_index = function_index

        if add_to_table:
            element_index = self.add_function_element(function_index)
        else:
            element_index = None

        return (function_index, element_index)

    def add_function_element(self, function_index):
        if not self.tables:
            self.add_table('funcref', limits=[1])
        else:
            self.tables[0].limits[0] += 1

        element_index = len(self.function_element_indexes)
        self.function_element_indexes.append(function_index)
        return element_index

    def add_function_type(self, function_type):
        key = self._function_type_key(function_type)
        if key not in self.function_types_map:
            self.function_types_map[key] = len(self.function_types)
            self.function_types.append(function_type)

        return self.function_types_map[key]

    def add_global(self, modifier, value_type, initializer, export_as=None):
        global_type = self.global_type(modifier, value_type)
        initializer = self.expression(initializer)
        global_index = len(self.globals)
        self.globals.append(parser.Global(global_type, initializer))

        export_as = self._export_as(export_as)
        if export_as is not None:
            self.export_global(export_as, global_index)

        return global_index

    def add_memory(self, limits, export_as=None):
        memory_index = len(self.memories)
        self.memories.append(self.memory_type(limits))

        export_as = self._export_as(export_as)
        if export_as is not None:
            self.export_memory(export_as, memory_index)

        return memory_index

    def add_table(self, reference_type, limits, export_as=None):
        export_as = self._export_as(export_as)
        table_index = len(self.tables)
        self.tables.append(self.table_type(reference_type, limits))

        export_as = self._export_as(export_as)
        if export_as is not None:
            self.export_table(export_as, table_index)

        return table_index

    def build_module(self):
        module = self.build_module_tree()
        return buffer.Buffer().write_module(module).getvalue()

    def build_module_tree(self):
        return parser.Module(
            type_section=parser.TypeSection(self.function_types),
            import_section=parser.ImportSection(self.imports),
            function_section=parser.FunctionSection(self.function_annotations),
            table_section=parser.TableSection(self.tables),
            memory_section=parser.MemorySection(self.memories),
            global_section=parser.GlobalSection(self.globals),
            export_section=parser.ExportSection(self.exports),
            start_section=None if self.start_function_index is None
                else parser.StartSection(self.start_function_index),
            element_section=None if not self.function_element_indexes
                else parser.ElementSection([
                    parser.DefaultSegment(
                        offset=[parser.i32_const(0)],
                        function_indexes=self.function_element_indexes,
                    ),
                ]),
            data_count_section=None if not self.data_segments
                else parser.DataCountSection(len(self.data_segments)),
            code_section=parser.CodeSection(self.function_bodies),
            data_section=parser.DataSection(self.data_segments),

            # Custom sections.
            custom1=self.leading_custom_sections,
            custom2=None,
            custom3=None,
            custom4=None,
            custom5=None,
            custom6=None,
            custom7=None,
            custom8=None,
            custom9=None,
            custom10=None,
            custom11=None,
            custom12=None,
            custom13=self.trailing_custom_sections,
        )

    def export(self, name, descriptor):
        self.exports.append(parser.Export(name, descriptor))

    def export_function(self, name, function_index):
        self._validate_export(name, function_index, prefix='function_')
        self.export(name, parser.ExportFunc(function_index))

    def export_global(self, name, global_index):
        self._validate_export(name, global_index, prefix='global_')
        self.export(name, parser.ExportGlobal(global_index))

    def export_memory(self, name, memory_index):
        self._validate_export(name, memory_index, prefix='memory_')
        self.export(name, parser.ExportMemory(memory_index))

    def export_table(self, name, table_index):
        self._validate_export(name, table_index, prefix='table_')
        self.export(name, parser.ExportTable(table_index))

    def expression(self, expression):
        if not isinstance(expression, list):
            expression = [expression]
        return [self.instruction(x) for x in expression]

    def function_type(self, parameter_types, result_types):
        if not isinstance(parameter_types, (list, str, tuple)):
            raise TypeError(
                f'Expected list, tuple, or str. Received: {type(parameter_types)}.'
            )

        if not isinstance(result_types, (list, str, tuple)):
            raise TypeError(
                f'Expected list, tuple, or str. Received: {type(result_types)}.'
            )

        if isinstance(parameter_types, str):
            parameter_types = [parameter_types]

        if isinstance(result_types, str):
            result_types = [result_types]

        assert isinstance(parameter_types, (list, tuple))
        assert isinstance(result_types, (list, tuple))

        for x in itertools.chain(parameter_types, result_types):
            if not isinstance(x, str):
                raise TypeError(
                    f'Expected list of str. Received element: {type(x)}.'
                )

        return parser.FunctionType(
            parameter_types=parameter_types,
            result_types=result_types,
        )

    def function_type_index(self, function_type):
        key = self._function_type_key(function_type)
        return self.function_types_map.get(key, -1)

    def global_type(self, modifier, value_type):
        modifiers = ['const', 'var']
        if not isinstance(modifier, str) or modifier not in modifiers:
            raise TypeError(
                f'Expected modifier in {modifiers}. Received: {modifier!r}.'
            )
        value_type = self.value_type(value_type)
        return parser.GlobalType(value_type, modifier)

    def instruction(self, instruction):
        if not isinstance(instruction, (list, str, tuple)):
            return instruction

        if isinstance(instruction, str):
            instruction = (instruction,)

        assert isinstance(instruction, (list, tuple))
        name, args = instruction[0], instruction[1:]

        if not isinstance(name, str):
            raise TypeError(
                f'Expected instruction to be a str. Received: {type(name)}.'
            )

        class_name = name.replace('.', '_')

        if not hasattr(parser, class_name):
            raise TypeError(f'Unknown instruction: {instruction!r}.')

        cls = getattr(parser, class_name)
        return cls(*args)

    def import_descriptor(self, module, name, descriptor):
        self.imports.append(parser.Import(module, name, descriptor))

    def import_function(self, module, name, parameter_types, result_types):
        ft = self.function_type(parameter_types, result_types)
        self.add_function_type(ft)
        index = self.function_type_index(ft)
        return self.import_descriptor(module, name, parser.ImportFunc(index))

    def import_global(self, module, name, modifier, value_type):
        global_type = self.global_type(modifier, value_type)
        self.import_descriptor(module, name, parser.ImportGlobal(global_type))

    def import_memory(self, module, name, limits):
        memory_type = self.memory_type(limits)
        self.import_descriptor(module, name, parser.ImportMemory(memory_type))

    def import_table(self, module, name, reference_type, limits):
        reference_type = self.reference_type(reference_type)
        limits = self.limits(limits)
        table_type = parser.TableType(reference_type, limits)
        self.import_descriptor(module, name, parser.ImportTable(table_type))

    def limits(self, limits):
        if isinstance(limits, (list, tuple)):
            if len(limits) == 1:
                return self.limits(parser.MinLimit(limits[0]))
            if len(limits) == 2:
                return self.limits(parser.MinMaxLimits(*limits))
            raise TypeError(
                f'Expected list or tuple of one or two elements. Received {len(limits)}.'
            )

        if not isinstance(limits, (parser.MinLimit, parser.MinMaxLimits)):
            raise TypeError(
                'Expected list, tuple, MinLimit, or MinMaxLimit object.'
                f' Received: {type(limits)}.'
            )

        min = limits.min
        if not isinstance(min, int):
            raise TypeError(f'Minimum limit must be an int. Received: {type(min)}.')

        if min < 0:
            raise TypeError(f'Minimum limit must be >= 0. Received: {min}.')

        if isinstance(limits, parser.MinLimit):
            return limits

        max = limits.max
        if not isinstance(max, int):
            raise TypeError(f'Max limit must be an int. Received: {type(max)}.')

        if max < min:
            raise TypeError(
                f'Max limit must not be less than minimum. Received: {(min, max)}.'
            )

        return limits

    def memory_type(self, limits):
        return parser.MemoryType(self.limits(limits))

    def reference_type(self, reference_type):
        expected = self.reference_types
        if not isinstance(reference_type, str) or reference_type not in expected:
            raise TypeError(
                f'Expected one of {expected!r}. Received: {reference_type!r}'
            )
        return reference_type

    def set_function_body(self, function_index, expression):
        if not (0 <= function_index < len(self.function_bodies)):
            raise ValueError(
                f'function_index out of range [0, {len(self.function_bodies)}).'
            )

        entry = self.function_bodies[function_index]
        was = entry.expression
        entry.expression = self.expression(expression)
        return was

    def table_type(self, reference_type, limits):
        reference_type = self.reference_type(reference_type)
        limits = self.limits(limits)
        return parser.TableType(reference_type, limits)

    def value_type(self, value_type):
        expected = self.value_types
        if not isinstance(value_type, str) or value_type not in expected:
            raise TypeError(
                f'Expected one of {expected!r}. Received: {value_type!r}'
            )
        return value_type

    def _export_as(self, export_as):
        if export_as is not None and not isinstance(export_as, str):
            raise Exception(
                'The export_as argument must be either None or a str.'
                f' Received: {type(export_as)}.'
            )
        return export_as

    def _function_type_key(self, function_type):
        params = tuple(function_type.parameter_types)
        res = tuple(function_type.result_types)
        return (params, res)

    def _validate_export(self, name, index, prefix=''):
        if not isinstance(name, str):
            raise TypeError(
                'The name argument must be a str.'
                f' Received: {type(name)}.'
            )

        if not isinstance(index, int):
            raise TypeError(
                f'The {prefix}index argument must be an int.'
                f' Received {type(index)}.'
            )
