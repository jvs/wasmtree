from wasmtree.buffer import Buffer
from wasmtree import parser


def test_custom_section():
    expected = parser.CustomSection(
        name='test',
        body=b'\x12\x34\x56',
    )

    doc = Buffer().write_custom_section(expected).getvalue()
    assert doc == b'\x00\x08\x04test\x12\x34\x56'

    received = parser.CustomSection.parse(doc)
    assert received == expected


def test_type_section():
    expected = [
        parser.FuncType(
            params=['i32'],
            results=['i64'],
        ),
        parser.FuncType(
            params=['i32', 'i64'],
            results=['f32', 'f64'],
        ),
        parser.FuncType(
            params=[],
            results=[],
        ),
    ]

    doc = Buffer().write_type_section(expected).getvalue()
    received = parser.TypeSection.parse(doc)
    assert received.func_types == expected
