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

    def write_f32(self, value):
        self.write_bytes(struct.pack('<f', value))
        return self

    def write_f64(self, value):
        self.write_bytes(struct.pack('<d', value))
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

    def write_u32(self, value):
        assert isinstance(value, int)
        assert 0 <= value <= (2 ** 32)
        self._write_unsigned_integer(value)
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