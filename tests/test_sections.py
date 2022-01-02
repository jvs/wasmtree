from wasmtree.buffer import Buffer
from wasmtree import parser


def test_custom_section():
    expected = parser.CustomSection(
        name='test',
        body=b'\x12\x34\x56',
    )

    contents = Buffer().write_custom_section(expected).getvalue()
    assert contents == b'\x00\x08\x04test\x12\x34\x56'

    received = parser.CustomSection.parse(contents)
    assert received == expected


def test_type_section():
    expected = parser.TypeSection([
        parser.FunctionType(
            parameter_types=['i32'],
            result_types=['i64'],
        ),
        parser.FunctionType(
            parameter_types=['i32', 'i64'],
            result_types=['f32', 'f64'],
        ),
        parser.FunctionType(
            parameter_types=[],
            result_types=[],
        ),
    ])

    contents = Buffer().write_type_section(expected).getvalue()
    received = parser.TypeSection.parse(contents)
    assert received == expected


def test_function_section():
    expected = parser.FunctionSection([0, 1, 2, 3, 2 ** 31 - 1, 3, 0, 2, 0, 1, 0])
    contents = Buffer().write_function_section(expected).getvalue()
    received = parser.FunctionSection.parse(contents)
    assert received == expected


def test_code_section():
    expected = parser.CodeSection([
        parser.CodeEntry(
            locals=[],
            expression=[parser.nop(), parser.nop()],
        ),
    ])
    contents = Buffer().write_code_section(expected).getvalue()
    received = parser.CodeSection.parse(contents)
    assert received == expected
