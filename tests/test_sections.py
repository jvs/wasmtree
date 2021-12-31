from wasmtree.buffer import Buffer
from wasmtree import parser


def test_custom_section():
    buf = Buffer()
    buf.write_byte(0x00)
    buf.write_u32(8)
    buf.write_name('test')
    buf.write_bytes(b'\x12\x34\x56')
    doc = buf.getvalue()
    assert len(doc) == 10

    received = parser.CustomSection.parse(doc)
    assert received == parser.CustomSection(
        id=0x00,
        size=8,
        name='test',
        body=doc[2:],
    )


def test_type_section():
    stage = Buffer()

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

    stage.write_u32(len(expected))
    for func_type in expected:
        stage.write_type(func_type)

    stage_bytes = stage.getvalue()

    buf = Buffer()
    buf.write_byte(0x01)
    buf.write_u32(len(stage_bytes))
    buf.write_bytes(stage_bytes)
    doc = buf.getvalue()

    received = parser.TypeSection.parse(doc)
    assert received.func_types == expected
