import random

from wasmtree.buffer import Buffer
from wasmtree import parser


def test_unsigned_integers():
    numbers = list(range(2 ** 11 + 8))

    for pow in range(12, 31):
        numbers.extend([
            2 ** pow - 2,
            2 ** pow - 1,
            2 ** pow - 0,
            2 ** pow + 1,
            2 ** pow + 2,
        ])

    numbers.extend([
        2 ** 32 - 2,
        2 ** 32 - 1,
        2 ** 32 - 0,
    ])

    for num in numbers:
        bytes = Buffer().write_u32(num).getvalue()
        received = parser.u32.parse(bytes)
        assert received == num


def test_signed_integers():
    numbers = list(range(-(2 ** 11 + 8), 2 ** 11 + 8))

    numbers.extend([
        -1 * (2 ** 31) + 0,
        -1 * (2 ** 31) + 1,
        -1 * (2 ** 31) + 2,
        (2 ** 31) - 1,
        (2 ** 31) - 2,
        (2 ** 31) - 3,
    ])

    for num in numbers:
        bytes = Buffer().write_i32(num).getvalue()
        received = parser.i32.parse(bytes)
        assert received == num


def test_floating_point_numbers():
    for _ in range(1000):
        # Get a random floating point number.
        num = random.uniform(-(2 ** 15), 2 ** 15)

        # Encode and decode the number using 32 bits.
        bytes = Buffer().write_f32(num).getvalue()
        expected = parser.f32.parse(bytes)

        # Now encode and decode again.
        bytes = Buffer().write_f32(expected).getvalue()
        received = parser.f32.parse(bytes)

        # Assert that it's the same number.
        assert received == expected

    # Now try f64.
    for _ in range(1000):
        # Get a random floating point number.
        num = random.uniform(-(2 ** 31), 2 ** 31)

        # Encode and decode the number using 64 bits.
        bytes = Buffer().write_f64(num).getvalue()
        expected = parser.f64.parse(bytes)

        # Now encode and decode again.
        bytes = Buffer().write_f64(expected).getvalue()
        received = parser.f64.parse(bytes)

        # Assert that it's the same number.
        assert received == expected


def test_names():
    names = [
        '',
        'foo',
        'bar',
        'baz',
        '\x00',
        'zim\x00',
        'zam\0',
        '"fiz"',
        "'buz'",
    ]
    for name in names:
        bytes = Buffer().write_name(name).getvalue()
        received = parser.name.parse(bytes)
        assert received == name

