#!/usr/bin/python3

import textwrap
import unittest
from collections import namedtuple

MsgType = namedtuple('MsgCode', "statement separator begin end sizable")


class ZetaMessage:
    """Represents the Message to zeta. It holds the messages' information for
    code generation"""
    def __init__(self,
                 name: str,
                 mtype: str = '',
                 size: int = 0,
                 description: str = "",
                 fields: list = None,
                 parent: object = None,
                 level: int = 0) -> None:
        """ZetaMessage constructor.

        :param name: the message name
        :param mtype: the message type. It can be struct, union,
        bitarray_<type>, bits and all the s<size> or u<size>. Where <size> is 8,
        16, 32 and 64 and <type> is all the possible s<size> or u<size>.
        For example: a message can have a mtype of u8 or bitarray_s64.
        :param size: the message size in bytes. If you want to define an array message
        of 5 items of u32 you must define the array size 5 and mtype u32.
        The result will be an 'uint32_t value[5]' as value.
        :param description: the message description. It is used for
        documentation only. No code is generated based on this parameter.
        :param fields: the messagem fields when it is of mtype struct, union or bitarray.
        :param parent: the message parent to point back up to the parent.
        For example: an struct field know its parent by this parameter.
        :param level: the messagem level. When the message is inside another
        message, it receives the level increment.
        :returns: None
        :rtype: None

        """
        self.name = name.lower()
        self.size = size
        self.level = level
        self.description = description
        self.parent = parent
        self.mtype_obj = None
        if "bitarray" in mtype:  # mtype here must be bitarray_u32 for example
            self.mtype, self.mtype_base_type = mtype.lower().split("_")
        else:
            self.mtype = mtype.lower()
            # used by the children of an bitarray
            self.mtype_base_type = "u32"
        if self.size > 0 and self.mtype not in [
                'bits', 'u8', 's8', 'u16', 's16', 'u32', 's32', 'u64', 's64'
        ]:
            assert self.level > 0, "Invalid size for root objects"
        self.digest_type()
        self.fields = []
        if fields is not None:
            for field in fields:
                for item_name, sub_fields in field.items():
                    self.fields.append(
                        ZetaMessage(item_name,
                                    level=self.level + 1,
                                    parent=self,
                                    **sub_fields))

    def __repr__(self):
        message_repr = []
        for k, v in self.__dict__.items():
            if k not in ["parent", "size"]:
                message_repr.append("\n" +
                                    textwrap.indent(f"{k}: {v}", "    " *
                                                    (self.level + 1)))
        return f"Message({''.join(message_repr)});"

    def digest_type(self) -> None:
        """Digests the mtype and mounts the necessary data to the code
        generation.

        :returns: None
        :rtype: None

        """
        if self.mtype == 'struct':
            self.mtype_obj = MsgType(
                statement="struct __attribute__((__packet__))"
                if self.level > 0 else f"struct {self.name}",
                separator="\n",
                begin="{\n",
                end="\n} __attribute__((__packed__))",
                sizable=f"[{self.size}]" if self.size > 0 else "")
            self.name = "" if self.level == 0 else " " + self.name
        elif self.mtype == 'union':
            self.mtype_obj = MsgType(
                statement="union" if self.level > 0 else f"union {self.name}",
                separator="\n",
                begin="{\n",
                end="\n}",
                sizable=f"[{self.size}]" if self.size > 0 else "")
            self.name = "" if self.level == 0 else " " + self.name
        elif self.mtype == "bitarray":
            self.mtype_obj = MsgType(
                statement="struct"
                if self.level > 0 else f"struct {self.name}",
                separator="\n",
                begin="{\n",
                end="\n}",
                sizable=f"[{self.size}]" if self.size > 0 else "")
            self.name = "" if self.level == 0 else " " + self.name

        elif self.mtype == "bits":
            radical = "uint{}_t"
            if self.mtype.startswith('s'):
                radical = "int{}_t"
            self.mtype_obj = MsgType(
                statement=radical.format(self.parent.mtype_base_type[1::])
                if self.parent else "uint32_t",
                separator="",
                begin="",
                end="",
                sizable=f":{self.size}" if self.size > 0 else "")
        else:
            if self.mtype in [
                    'u8', 's8', 'u16', 's16', 'u32', 's32', 'u64', 's64'
            ]:
                radical = "uint{}_t"
                if self.mtype.startswith('s'):
                    radical = "int{}_t"
                self.mtype_obj = MsgType(
                    statement=radical.format(self.mtype[1::]),
                    separator="",
                    begin="",
                    end="",
                    sizable=f"[{self.size}]" if self.size > 0 else "")
            else:
                raise TypeError(
                    f"The type {self.mtype} of field '{self.name}' is not valid."
                )

    def code(self) -> str:
        """Generates the code for the message.

        :returns: the code generated that represents the message
        :rtype: str

        """
        return textwrap.indent(
            f"{self.mtype_obj.statement} {self.mtype_obj.begin}{self.mtype_obj.separator.join([x.code() for x in self.fields])}{self.mtype_obj.end}{self.name}{self.mtype_obj.sizable};",
            prefix="    " * (1 if self.level > 0 else 0))


class TestStringMethods(unittest.TestCase):
    def test_primitives(self):
        self.assertEqual(
            "uint32_t var:1;",
            ZetaMessage('var', **{
                'mtype': 'bits',
                'size': 1
            }).code())
        self.assertEqual(
            "uint32_t var:10;",
            ZetaMessage('var', **{
                'mtype': 'bits',
                'size': 10
            }).code())
        self.assertEqual(
            "int8_t vars8b;",
            ZetaMessage('vars8b', **{
                'mtype': 's8',
                'size': 0
            }).code())
        self.assertEqual(
            "uint8_t var8b;",
            ZetaMessage('var8b', **{
                'mtype': 'u8',
                'size': 0
            }).code())
        self.assertEqual(
            "int16_t erwoeiruwoeirs16b;",
            ZetaMessage('erwoeiruwoeirs16b', **{
                'mtype': 's16',
                'size': 0
            }).code())
        self.assertEqual(
            "uint16_t var16bfff;",
            ZetaMessage('var16bfff', **{
                'mtype': 'u16',
                'size': 0
            }).code())
        self.assertEqual(
            "int32_t erwoeiru32b;",
            ZetaMessage('erwoeiru32b', **{
                'mtype': 's32',
                'size': 0
            }).code())
        self.assertEqual(
            "uint32_t var32fdd;",
            ZetaMessage('var32fdd', **{
                'mtype': 'u32',
                'size': 0
            }).code())
        self.assertEqual(
            "int64_t erw64iru32b;",
            ZetaMessage('erw64iru32b', **{
                'mtype': 's64',
                'size': 0
            }).code())

        self.assertEqual(
            "    int64_t erw64iru32b;",
            ZetaMessage('erw64iru32b', **{
                'mtype': 's64',
                'size': 0
            }, level=1).code())
        self.assertEqual(
            "    int64_t erw64iru32b;",
            ZetaMessage('erw64iru32b', **{
                'mtype': 's64',
                'size': 0
            }, level=4).code())

    def test_struct_simple(self):
        self.assertEqual(
            "struct my_struct {\n\n};",
            ZetaMessage('my_struct', **{
                'mtype': 'struct',
                'fields': []
            }).code())
        self.assertEqual(
            "struct my_struct {\n    int64_t var64bits;\n};",
            ZetaMessage(
                'my_struct', **{
                    'mtype': 'struct',
                    'fields': [{
                        'var64bits': {
                            'mtype': 's64'
                        }
                    }]
                }).code())
        self.assertEqual(
            "struct my_struct {\n    int64_t var64bits;\n    uint32_t var32;\n    int16_t var16s;\n};",
            ZetaMessage(
                'my_struct', **{
                    'mtype':
                    'struct',
                    'fields': [{
                        'var64bits': {
                            'mtype': 's64'
                        },
                        'var32': {
                            'mtype': 'u32'
                        },
                        'var16s': {
                            'mtype': 's16'
                        }
                    }]
                }).code())
        self.assertEqual(
            textwrap.indent(
                "struct {\n    int64_t var64bits;\n    uint32_t var32;\n    int16_t var16s;\n} my_struct;",
                prefix="    "),
            ZetaMessage('my_struct',
                        level=1,
                        **{
                            'mtype':
                            'struct',
                            'fields': [{
                                'var64bits': {
                                    'mtype': 's64'
                                },
                                'var32': {
                                    'mtype': 'u32'
                                },
                                'var16s': {
                                    'mtype': 's16'
                                }
                            }]
                        }).code())
        self.assertEqual(
            textwrap.indent(
                "struct {\n    int64_t var64bits;\n    uint32_t var32;\n    int16_t var16s;\n} my_struct[128];",
                prefix="    "),
            ZetaMessage('my_struct',
                        level=1,
                        **{
                            'mtype':
                            'struct',
                            'size':
                            128,
                            'fields': [{
                                'var64bits': {
                                    'mtype': 's64'
                                },
                                'var32': {
                                    'mtype': 'u32'
                                },
                                'var16s': {
                                    'mtype': 's16'
                                }
                            }]
                        }).code())

    def test_union_simple(self):
        self.assertEqual(
            "union my_union {\n\n};",
            ZetaMessage('my_union', **{
                'mtype': 'union',
                'fields': []
            }).code())
        self.assertEqual(
            "union my_union {\n    int64_t v64s;\n};",
            ZetaMessage(
                'my_union', **{
                    'mtype': 'union',
                    'fields': [{
                        'v64s': {
                            'mtype': 's64'
                        }
                    }]
                }).code())
        self.assertEqual(
            "union my_union {\n    int64_t v64s;\n    uint32_t v32;\n};",
            ZetaMessage(
                'my_union', **{
                    'mtype': 'union',
                    'fields': [{
                        'v64s': {
                            'mtype': 's64'
                        },
                        'v32': {
                            'mtype': 'u32'
                        }
                    }]
                }).code())
        self.assertEqual(
            textwrap.indent("union {\n    int64_t v64s;\n} my_union;",
                            prefix="    "),
            ZetaMessage(
                'my_union', **{
                    'level': 1,
                    'mtype': 'union',
                    'fields': [{
                        'v64s': {
                            'mtype': 's64'
                        }
                    }]
                }).code())
        self.assertEqual(
            textwrap.indent(
                "union {\n    int64_t v64s;\n    uint32_t v32;\n} my_union;",
                prefix="    "),
            ZetaMessage(
                'my_union', **{
                    'level': 1,
                    'mtype': 'union',
                    'fields': [{
                        'v64s': {
                            'mtype': 's64'
                        },
                        'v32': {
                            'mtype': 'u32'
                        }
                    }]
                }).code())

    def test_bitarray_simple(self):
        self.assertEqual(
            "struct my_bitarray {\n\n};",
            ZetaMessage('my_bitarray', **{
                'mtype': 'bitarray_u32',
                'fields': []
            }).code())
        self.assertEqual(
            "struct my_bitarray {\n    uint32_t b2:2;\n};",
            ZetaMessage(
                'my_bitarray', **{
                    'mtype': 'bitarray_u32',
                    'fields': [{
                        'b2': {
                            'mtype': 'bits',
                            'size': 2
                        }
                    }]
                }).code())
        self.assertEqual(
            "struct my_bitarray {\n    uint32_t b2:2;\n    uint32_t b8:8;\n};",
            ZetaMessage(
                'my_bitarray', **{
                    'mtype':
                    'bitarray_u32',
                    'fields': [{
                        'b2': {
                            'mtype': 'bits',
                            'size': 2
                        },
                        'b8': {
                            'mtype': 'bits',
                            'size': 8
                        }
                    }]
                }).code())
        self.assertEqual(
            textwrap.indent(
                "struct {\n    uint32_t b2:2;\n    uint32_t b8:8;\n} my_bitarray;",
                prefix="    "),
            ZetaMessage('my_bitarray',
                        level=1,
                        **{
                            'mtype':
                            'bitarray_u32',
                            'fields': [{
                                'b2': {
                                    'mtype': 'bits',
                                    'size': 2
                                },
                                'b8': {
                                    'mtype': 'bits',
                                    'size': 8
                                }
                            }]
                        }).code())
        self.assertEqual(
            textwrap.indent(
                "struct {\n    uint32_t b2:2;\n    uint32_t b8:8;\n} my_bitarray[64];",
                prefix="    "),
            ZetaMessage('my_bitarray',
                        level=1,
                        size=64,
                        **{
                            'mtype':
                            'bitarray_u32',
                            'fields': [{
                                'b2': {
                                    'mtype': 'bits',
                                    'size': 2
                                },
                                'b8': {
                                    'mtype': 'bits',
                                    'size': 8
                                }
                            }]
                        }).code())

    def test_array_simple(self):
        self.assertEqual(
            "int8_t vars8b[1];",
            ZetaMessage('vars8b', **{
                'mtype': 's8',
                'size': 1
            }).code())
        self.assertEqual(
            "uint8_t var8b[10];",
            ZetaMessage('var8b', **{
                'mtype': 'u8',
                'size': 10
            }).code())
        self.assertEqual(
            "int16_t erwoeiruwoeirs16b[128];",
            ZetaMessage('erwoeiruwoeirs16b', **{
                'mtype': 's16',
                'size': 128
            }).code())
        self.assertEqual(
            "    uint16_t var16bfff[1000];",
            ZetaMessage('var16bfff', level=5, **{
                'mtype': 'u16',
                'size': 1000
            }).code())
        self.assertEqual(
            "int32_t erwoeiru32b[7];",
            ZetaMessage('erwoeiru32b', **{
                'mtype': 's32',
                'size': 7
            }).code())
        self.assertEqual(
            "uint32_t var32fdd[35];",
            ZetaMessage('var32fdd', **{
                'mtype': 'u32',
                'size': 35
            }).code())
        self.assertEqual(
            "int64_t erw64iru32b[44];",
            ZetaMessage('erw64iru32b', **{
                'mtype': 's64',
                'size': 44
            }).code())

        self.assertEqual(
            "    int64_t erw64iru32b[9999];",
            ZetaMessage('erw64iru32b',
                        **{
                            'mtype': 's64',
                            'size': 9999
                        },
                        level=1).code())
        self.assertEqual(
            "    int64_t erw64iru32b[157869];",
            ZetaMessage('erw64iru32b',
                        **{
                            'mtype': 's64',
                            'size': 157869
                        },
                        level=4).code())

    def test_complex_message(self):
        self.assertEqual(
            textwrap.indent("", prefix="    "),
            ZetaMessage('req',
                        level=0,
                        **{
                            'mtype':
                            'struct',
                            'fields': [{
                                'id': {
                                    'mtype': 'u32'
                                },
                                'flag': {
                                    'mtype':
                                    'bitarray_u8',
                                    'fields': [{
                                        'read': {
                                            'mtype': 'bits',
                                            'size': 1
                                        }
                                    }, {
                                        'write': {
                                            'mtype': 'bits',
                                            'size': 1
                                        }
                                    }, {
                                        'erase': {
                                            'mtype': 'bits',
                                            'size': 1
                                        }
                                    }, {
                                        'update': {
                                            'mtype': 'bits',
                                            'size': 1
                                        }
                                    }]
                                },
                                'bytes': {
                                    'mtype': 'u8',
                                    'size': 32
                                },
                                'complex': {
                                    'mtype':
                                    'union',
                                    'fields': [{
                                        'arr': {
                                            'mtype': 'u32',
                                            'size': 128,
                                        },
                                        'st': {
                                            'mtype':
                                            'struct',
                                            'size':
                                            4,
                                            'fields': [{
                                                'number': {
                                                    'mtype': 's64',
                                                    'size': 32
                                                }
                                            }]
                                        }
                                    }]
                                }
                            }]
                        }).code())
        self.assertEqual(
            textwrap.indent("", prefix="    "),
            ZetaMessage(
                'req', **{
                    'mtype':
                    'struct',
                    'fields': [{
                        'id': {
                            'mtype': 'u32'
                        },
                        'flag': {
                            'mtype':
                            'bitarray_u8',
                            'fields': [{
                                'read': {
                                    'mtype': 'bits',
                                    'size': 1
                                },
                                'write': {
                                    'mtype': 'bits',
                                    'size': 1
                                },
                                'erase': {
                                    'mtype': 'bits',
                                    'size': 1
                                },
                                'update': {
                                    'mtype': 'bits',
                                    'size': 1
                                }
                            }]
                        },
                        'bytes': {
                            'mtype': 'u8',
                            'size': 32
                        }
                    }]
                }).code())


if __name__ == "__main__":
    unittest.main()
