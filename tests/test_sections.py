from wasmtree.buffer import Buffer
from wasmtree import parser


def test_custom_section():
    doc = Buffer().write_custom_section('test', b'\x12\x34\x56').getvalue()
    assert len(doc) == 10
    received = parser.CustomSection.parse(doc)

    assert received == parser.CustomSection(
        id=0x00,
        size=8,
        name='test',
        body=b'\x12\x34\x56',
    )


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
