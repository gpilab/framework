# -*- coding: utf-8 -*-
# Protocol buffer code for gpi.proto — updated for protobuf >= 4.21
# To regenerate from source run:
#   python -m grpc_tools.protoc -I gpi --python_out=gpi --grpc_python_out=gpi gpi/gpi.proto
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()

DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(
    b'\n\tgpi.proto\")\n\x07Request\x12\x10\n\x08\x66unction\x18\x01'
    b' \x01(\x0c\x12\x0c\n\x04\x61rgs\x18\x02 \x01(\x0c\"\x18\n\x06'
    b'Result\x12\x0e\n\x06result\x18\x01 \x01(\x0c\x32!\n\x03GPI\x12'
    b'\x1a\n\x03run\x12\x08.Request\x1a\x07.Result\"\x00\x62\x06proto3'
)

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'gpi_pb2', globals())
# @@protoc_insertion_point(module_scope)
