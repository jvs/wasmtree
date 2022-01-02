import wasmer

from wasmtree import Builder, Buffer, parser


def test_simple_module():
    contents = wasmer.wat2wasm('''
        (module
            (type $add_one_t (func (param i32) (result i32)))
            (func $add_one_f (type $add_one_t) (param $value i32) (result i32)
                local.get $value
                i32.const 1
                i32.add)
            (export "add_one" (func $add_one_f)))
    ''')
    expected_module = parser.Module.parse(contents)

    builder = Builder()
    builder.add_function(
        parameter_types=['i32'],
        result_types='i32',
        local_types=[],
        expression=[
            ('local.get', 0),
            ('i32.const', 1),
            'i32.add',
        ],
        export_as='add_one',
    )

    builder.add_custom_section(
        name=expected_module.custom12[0].name,
        body=expected_module.custom12[0].body,
    )
    module = builder.build_module()

    assert module.type_section == parser.TypeSection([
        parser.FunctionType(['i32'], ['i32']),
    ])

    assert module.function_section == parser.FunctionSection([0])

    assert module.export_section == parser.ExportSection([
        parser.Export(name='add_one', descriptor=parser.ExportFunc(0))
    ])

    assert module.code_section == parser.CodeSection([
        parser.CodeEntry(
            locals=[],
            expression=[
                parser.local_get(0),
                parser.i32_const(1),
                parser.i32_add(),
            ],
        ),
    ])

    received = Buffer().write_module(module).getvalue()
    assert received == contents
