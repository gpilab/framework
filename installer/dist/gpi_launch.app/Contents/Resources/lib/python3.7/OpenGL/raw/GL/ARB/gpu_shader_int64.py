'''Autogenerated by xml_generate script, do not edit!'''
from OpenGL import platform as _p, arrays
# Code generation uses this
from OpenGL.raw.GL import _types as _cs
# End users want this...
from OpenGL.raw.GL._types import *
from OpenGL.raw.GL import _errors
from OpenGL.constant import Constant as _C

import ctypes
_EXTENSION_NAME = 'GL_ARB_gpu_shader_int64'
def _f( function ):
    return _p.createFunction( function,_p.PLATFORM.GL,'GL_ARB_gpu_shader_int64',error_checker=_errors._error_checker)
GL_INT64_ARB=_C('GL_INT64_ARB',0x140E)
GL_INT64_VEC2_ARB=_C('GL_INT64_VEC2_ARB',0x8FE9)
GL_INT64_VEC3_ARB=_C('GL_INT64_VEC3_ARB',0x8FEA)
GL_INT64_VEC4_ARB=_C('GL_INT64_VEC4_ARB',0x8FEB)
GL_UNSIGNED_INT64_ARB=_C('GL_UNSIGNED_INT64_ARB',0x140F)
GL_UNSIGNED_INT64_VEC2_ARB=_C('GL_UNSIGNED_INT64_VEC2_ARB',0x8FF5)
GL_UNSIGNED_INT64_VEC3_ARB=_C('GL_UNSIGNED_INT64_VEC3_ARB',0x8FF6)
GL_UNSIGNED_INT64_VEC4_ARB=_C('GL_UNSIGNED_INT64_VEC4_ARB',0x8FF7)
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,arrays.GLint64Array)
def glGetUniformi64vARB(program,location,params):pass
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,arrays.GLuint64Array)
def glGetUniformui64vARB(program,location,params):pass
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,_cs.GLsizei,arrays.GLint64Array)
def glGetnUniformi64vARB(program,location,bufSize,params):pass
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,_cs.GLsizei,arrays.GLuint64Array)
def glGetnUniformui64vARB(program,location,bufSize,params):pass
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,_cs.GLint64)
def glProgramUniform1i64ARB(program,location,x):pass
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,_cs.GLsizei,arrays.GLint64Array)
def glProgramUniform1i64vARB(program,location,count,value):pass
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,_cs.GLuint64)
def glProgramUniform1ui64ARB(program,location,x):pass
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,_cs.GLsizei,arrays.GLuint64Array)
def glProgramUniform1ui64vARB(program,location,count,value):pass
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,_cs.GLint64,_cs.GLint64)
def glProgramUniform2i64ARB(program,location,x,y):pass
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,_cs.GLsizei,arrays.GLint64Array)
def glProgramUniform2i64vARB(program,location,count,value):pass
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,_cs.GLuint64,_cs.GLuint64)
def glProgramUniform2ui64ARB(program,location,x,y):pass
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,_cs.GLsizei,arrays.GLuint64Array)
def glProgramUniform2ui64vARB(program,location,count,value):pass
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,_cs.GLint64,_cs.GLint64,_cs.GLint64)
def glProgramUniform3i64ARB(program,location,x,y,z):pass
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,_cs.GLsizei,arrays.GLint64Array)
def glProgramUniform3i64vARB(program,location,count,value):pass
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,_cs.GLuint64,_cs.GLuint64,_cs.GLuint64)
def glProgramUniform3ui64ARB(program,location,x,y,z):pass
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,_cs.GLsizei,arrays.GLuint64Array)
def glProgramUniform3ui64vARB(program,location,count,value):pass
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,_cs.GLint64,_cs.GLint64,_cs.GLint64,_cs.GLint64)
def glProgramUniform4i64ARB(program,location,x,y,z,w):pass
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,_cs.GLsizei,arrays.GLint64Array)
def glProgramUniform4i64vARB(program,location,count,value):pass
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,_cs.GLuint64,_cs.GLuint64,_cs.GLuint64,_cs.GLuint64)
def glProgramUniform4ui64ARB(program,location,x,y,z,w):pass
@_f
@_p.types(None,_cs.GLuint,_cs.GLint,_cs.GLsizei,arrays.GLuint64Array)
def glProgramUniform4ui64vARB(program,location,count,value):pass
@_f
@_p.types(None,_cs.GLint,_cs.GLint64)
def glUniform1i64ARB(location,x):pass
@_f
@_p.types(None,_cs.GLint,_cs.GLsizei,arrays.GLint64Array)
def glUniform1i64vARB(location,count,value):pass
@_f
@_p.types(None,_cs.GLint,_cs.GLuint64)
def glUniform1ui64ARB(location,x):pass
@_f
@_p.types(None,_cs.GLint,_cs.GLsizei,arrays.GLuint64Array)
def glUniform1ui64vARB(location,count,value):pass
@_f
@_p.types(None,_cs.GLint,_cs.GLint64,_cs.GLint64)
def glUniform2i64ARB(location,x,y):pass
@_f
@_p.types(None,_cs.GLint,_cs.GLsizei,arrays.GLint64Array)
def glUniform2i64vARB(location,count,value):pass
@_f
@_p.types(None,_cs.GLint,_cs.GLuint64,_cs.GLuint64)
def glUniform2ui64ARB(location,x,y):pass
@_f
@_p.types(None,_cs.GLint,_cs.GLsizei,arrays.GLuint64Array)
def glUniform2ui64vARB(location,count,value):pass
@_f
@_p.types(None,_cs.GLint,_cs.GLint64,_cs.GLint64,_cs.GLint64)
def glUniform3i64ARB(location,x,y,z):pass
@_f
@_p.types(None,_cs.GLint,_cs.GLsizei,arrays.GLint64Array)
def glUniform3i64vARB(location,count,value):pass
@_f
@_p.types(None,_cs.GLint,_cs.GLuint64,_cs.GLuint64,_cs.GLuint64)
def glUniform3ui64ARB(location,x,y,z):pass
@_f
@_p.types(None,_cs.GLint,_cs.GLsizei,arrays.GLuint64Array)
def glUniform3ui64vARB(location,count,value):pass
@_f
@_p.types(None,_cs.GLint,_cs.GLint64,_cs.GLint64,_cs.GLint64,_cs.GLint64)
def glUniform4i64ARB(location,x,y,z,w):pass
@_f
@_p.types(None,_cs.GLint,_cs.GLsizei,arrays.GLint64Array)
def glUniform4i64vARB(location,count,value):pass
@_f
@_p.types(None,_cs.GLint,_cs.GLuint64,_cs.GLuint64,_cs.GLuint64,_cs.GLuint64)
def glUniform4ui64ARB(location,x,y,z,w):pass
@_f
@_p.types(None,_cs.GLint,_cs.GLsizei,arrays.GLuint64Array)
def glUniform4ui64vARB(location,count,value):pass
