from . import parser


def run(instructions):
    if not instructions or not isinstance(instructions, list):
        return instructions

    result = []
    for instruction in instructions:
        # Drop nop instructions.
        if isinstance(instruction, parser.nop):
            continue

        # Replace [local.get N, local.set N] with [local.tee N].
        if (
            isinstance(instruction, parser.local_get)
            and result
            and isinstance(result[-1], parser.local_set)
            and instruction.index == result[-1].index
        ):
            result.pop()
            result.append(parser.local_tee(instruction.index))
            continue

        # Precompute some constant values.
        if (
            _is_binary_operator(instruction)
            and len(result) >= 2
            and _is_constant(result[-1])
            and _is_constant(result[-2])
        ):
            const2 = result.pop()
            const1 = result.pop()
            result.extend(_precompute(const1, const2, instruction))
            continue

        # Apply the optimizations to any field that is a list of instructions.
        if isinstance(instruction, parser.Node):
            updates = {}
            for field in instruction._fields:
                value = getattr(instruction, field)
                if isinstance(value, list):
                    updates[field] = run(value)
            if updates:
                instruction = instruction._replace(**updates)

        result.append(instruction)
    return result


def _is_binary_operator(instruction):
    if not isinstance(instruction, parser.Node):
        return False

    name = type(instruction).__name__
    if '_' not in name:
        return False

    type_name, op_name = name.split('_', 1)

    if type_name not in ['i32', 'i64', 'f32', 'f64']:
        return False

    types = ['i32', 'i64', 'f32', 'f64']
    ops = [
        'add',
        'and',
        'copysign',
        'div',
        'div_s',
        'div_u',
        'eq',
        'ge',
        'ge_s',
        'ge_u',
        'gt',
        'gt_s',
        'gt_u',
        'le',
        'le_s',
        'le_u',
        'lt',
        'lt_s',
        'lt_u',
        'max',
        'min',
        'mul',
        'ne',
        'or',
        'rem_s',
        'rem_u',
        'rotl',
        'rotr',
        'shl',
        'shr_s',
        'shr_u',
        'sub',
        'xor',
    ]
    return type_name in types and op_name in ops


def _is_constant(instruction):
    return isinstance(instruction, (
        parser.f32_const,
        parser.f64_const,
        parser.i32_const,
        parser.i64_const,
    ))


def _precompute(const1, const2, instruction):
    t1 = type(const1).__name__.split('_', 1)[0]
    t2 = type(const2).__name__.split('_', 1)[0]
    t3, op_name = type(instruction).__name__.split('_', 1)

    # If the types aren't all the same, then who knows what's going on here.
    # Just leave the sequence alone.
    if t1 != t2 or t2 != t3:
        return [const1, const2, instruction]

    result = None

    # Just handle a few operators for now.
    if op_name == 'add':
        result = const1.number + const2.number
    elif op_name == 'eq':
        result = const1.number == const2.number
    elif op_name == 'mul':
        result = const1.number * const2.number
    elif op_name == 'ne':
        result = const1.number != const2.number
    elif op_name == 'sub':
        result = const1.number - const2.number

    if isinstance(result, bool):
        return [parser.i32_const(number=int(result))]

    # If the result overflows, then just leave the sequence alone for now.
    if result is not None and _within_bounds(t1, result):
        return [const1._replace(number=result)]

    # This operation must not be implemented yet. Just leave the sequence alone.
    return [const1, const2, instruction]


def _within_bounds(type_name, number):
    if type_name == 'f32' and type_name == 'f64':
        return True
    # For now, be pretty conservative about the values that we'll precompute.
    if type_name == 'i32':
        return 0 <= number <= (2 ** 30)
    if type_name == 'i64':
        return 0 <= number <= (2 ** 60)
    return False
