#pragma once

#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <cstdlib>
#include <iostream>
#include <mutex>
#include <streambuf>
#include <string>

namespace gpi {

class PythonStdoutBuffer final : public std::streambuf {
public:
    explicit PythonStdoutBuffer(std::streambuf* fallback) : fallback_(fallback) {}

protected:
    int overflow(int character) override {
        if (character == traits_type::eof())
            return sync() == 0 ? traits_type::not_eof(character) : traits_type::eof();

        bool flush = false;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            pending_.push_back(static_cast<char>(character));
            flush = character == '\n';
        }
        return flush && sync() != 0 ? traits_type::eof() : character;
    }

    std::streamsize xsputn(const char* text, std::streamsize count) override {
        bool flush = false;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            pending_.append(text, static_cast<size_t>(count));
            flush = pending_.find('\n') != std::string::npos;
        }
        return flush && sync() != 0 ? 0 : count;
    }

    int sync() override {
        std::string text;
        {
            std::lock_guard<std::mutex> lock(mutex_);
            text.swap(pending_);
        }
        if (text.empty())
            return 0;

        if (!Py_IsInitialized()) {
            fallback_->sputn(text.data(), static_cast<std::streamsize>(text.size()));
            return fallback_->pubsync();
        }

        const PyGILState_STATE gil = PyGILState_Ensure();
        PyObject* python_stdout = PySys_GetObject("stdout");
        PyObject* message = PyUnicode_DecodeUTF8(
            text.data(), static_cast<Py_ssize_t>(text.size()), "replace");
        PyObject* write = python_stdout ? PyObject_GetAttrString(python_stdout, "write") : nullptr;
        PyObject* result = write != nullptr && message != nullptr
            ? PyObject_CallOneArg(write, message) : nullptr;
        Py_XDECREF(write);
        Py_XDECREF(message);
        if (result != nullptr) {
            Py_DECREF(result);
        } else {
            PyErr_Clear();
            fallback_->sputn(text.data(), static_cast<std::streamsize>(text.size()));
            fallback_->pubsync();
        }
        PyGILState_Release(gil);
        return 0;
    }

private:
    std::streambuf* fallback_;
    std::mutex mutex_;
    std::string pending_;
};

class PythonStdoutInstaller final {
public:
    PythonStdoutInstaller() : buffer_(std::cout.rdbuf()) {
        if (std::getenv("GPI_WORKER_MODE") != nullptr)
            std::cout.rdbuf(&buffer_);
    }

private:
    PythonStdoutBuffer buffer_;
};

static PythonStdoutInstaller gpi_python_stdout_installer;

}  // namespace gpi