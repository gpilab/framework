# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

from . import gpi_pb2 as gpi__pb2


class GPIStub(object):
    """The greeting service definition.
    """

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.run = channel.unary_unary(
                '/GPI/run',
                request_serializer=gpi__pb2.Request.SerializeToString,
                response_deserializer=gpi__pb2.Result.FromString,
                )


class GPIServicer(object):
    """The greeting service definition.
    """

    def run(self, request, context):
        """Sends a greeting
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_GPIServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'run': grpc.unary_unary_rpc_method_handler(
                    servicer.run,
                    request_deserializer=gpi__pb2.Request.FromString,
                    response_serializer=gpi__pb2.Result.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'GPI', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class GPI(object):
    """The greeting service definition.
    """

    @staticmethod
    def run(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/GPI/run',
            gpi__pb2.Request.SerializeToString,
            gpi__pb2.Result.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
