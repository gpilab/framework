/*
 *   Copyright (C) 2014  Dignity Health
 *
 *   This program is free software: you can redistribute it and/or modify
 *   it under the terms of the GNU Lesser General Public License as published by
 *   the Free Software Foundation, either version 3 of the License, or
 *   (at your option) any later version.
 *
 *   This program is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU Lesser General Public License for more details.
 *
 *   You should have received a copy of the GNU Lesser General Public License
 *   along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 *   NO CLINICAL USE.  THE SOFTWARE IS NOT INTENDED FOR COMMERCIAL PURPOSES
 *   AND SHOULD BE USED ONLY FOR NON-COMMERCIAL RESEARCH PURPOSES.  THE
 *   SOFTWARE MAY NOT IN ANY EVENT BE USED FOR ANY CLINICAL OR DIAGNOSTIC
 *   PURPOSES.  YOU ACKNOWLEDGE AND AGREE THAT THE SOFTWARE IS NOT INTENDED FOR
 *   USE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITY, INCLUDING BUT NOT
 *   LIMITED TO LIFE SUPPORT OR EMERGENCY MEDICAL OPERATIONS OR USES.  LICENSOR
 *   MAKES NO WARRANTY AND HAS NOR LIABILITY ARISING FROM ANY USE OF THE
 *   SOFTWARE IN ANY HIGH RISK OR STRICT LIABILITY ACTIVITIES.
 */

/**
	\file threads.c
	\author Ken Johnson
	\date created: 2007.06.07

	\brief This library simplifies the implementation of threaded programing.

	This library simplifies threading by creating wrapper functions that complete the
	superflous overhead of threading. One of the main features is to be able to pass
	an arbitrary number of parameters rather than the single \a void \a * that the
	standard pthread_create() provides. Due to simplicity of implementing
	this framework only pointers can be passed to or returned from thread functions.
	This makes threading a trivial task to the end developer for many types of tasks.

	There are four functions of worth here, or better four types of funcitons that are
	useful to the end developer.
	- ::create_threads - useful for splitting a task. It creates the threads, and finishes execution
		before continuing in the current code. It is recommended to use a specific derivative
		of this	function such as ::create_threads4.
	- ::create_thread - useful for multitasking. This starts a specified thread, while continuing
		execution in the current code. Note that ::wait_thread must be used with this function.
		It is recommended to use a specific derivative of this function such as
		::create_thread4.
	- ::wait_thread - only used in conjunction with ::create_thread and its derivatives. This is
		used to wait for a specific thread to complete execution, and returns the return value of
		the thread.
	- ::pthread_create_va - works the same as the \a pthread_create, except that this is a variadic
		function, calling the passed function with all the parameters.

	\section examples Uesful Examples

	\subsection split Splitting a task
	This represents an example of performing threading by splitting a for loop. The function
	under consideration loops through a big dataset.
	\code
	void add (a, b, out)	{
		for (int i=0; i\<getsize(a); i++)	{
			get1 (out, i) = get1 (a, i) + get1 (b, i);
		}
	}
	...
		add (a, b, c);
	\endcode
	This is the alternative version that is threaded. Note that the function is not called directly. While
	there are two forms to call create_threads or create_threadsN, the later is recommended. Note
	that the \a num_threads and \a cur_thread are always necessary when using any of the
	::create_threads functions and are implicitly implied. When a ::create_threads function
	is used, the threads are started but execution of current code will pause until all
	the threads are completed.
	\code
	void add_thread (int *num_threads, int *cur_thread, a, b, out)	{
		int start = get_start(*num_threads, *cur_thread, getsize(a));
		int stop = get_stop(*num_threads, *cur_thread, getsize(a));
		for (int i=start; i\<stop; i++)	{
			get1 (out, i) = get1 (a, i) + get1 (b, i);
		}
	}
	...
		create_threads (10, add_thread, 3, a, b, c);
		// or the recommended way
		create_threads3 (10, add_thread, a, b, c);
	\endcode

	\subsection multitasking Multitasking Example
	This represents a small and simple example of performing threading to accomplish three different
	things simultaneously. This has profound differences from the version of threading that splits.
	When a ::create_thread function is called, the thread is created and started but execution
	of current code continues, uninterrupted. To make sure that the threads complete, a call to
	::wait_thread is needed, which will wait for the specific thread to finish. There is no
	guarantee on when execution will start on created threads. If ::wait_thread is not called,
	it is possible to exit the program and terminate all threads even before they finish.
	\code
	void transmit (int *data, float *rate, int *channel);
	void receive (int *data, int *channel);
	void process (int *rx_data, int *tx_data);

	int main ()	{
		int tx_data[100], rx_data[100];
		int rate, tx_channel, rx_channel;

		// create and start running threads
		pthread_t *tx_id = create_thread3 (transmit, tx_data, &rate, &tx_channel);
		pthread_t *rx_id = create_thread2 (receive, rx_data, &rx_channel);
		pthread_t *pro_id = create_thread2 (process, rx_data, tx_data);

		// wait for each thread to stop
		wait_thread (rx_id);
		wait_thread (pro_id);
		wait_thread (tx_id);
	}
	\endcode

	\subsection printing Printing Safely
		Two or more threads can simultaneously try to access the print buffer. This can provide
		garbled text. This type of scenario is called a data race. The solution is to avoid this
		is with a mutex (which is short for mutual exclusion).

		\code
		pthread_mutex_lock( &print_mutex );
		printf("thread %d is executing\n", *cur_thread);
		fflush(stdout);
		pthread_mutex_unlock( &print_mutex );
		\endcode

		Note that the \a print_mutex variable is already declared in this file (threads.c).
		<b>Don't forget to unlock mutexes</b>, or your code might become deadlocked.

	\subsection mutexing Avoiding Data Races Safely
		If a data race exists between two or more threads (like adding a value to the same
		memory location), additional precautions need to be incorporated. The most common and
		simplest approach is use mutexes to avoid these data races.

		See the above subsection on \ref printing for a simple example of using a mutex. One
		difference exists though with the prior example and a general case: the \a print_mutex
		is already created and ready to use. Intialization of mutexes can happen in two ways,
		by using the \a pthread_mutex_init function or by setting the variable directly to the
		value of \a PTHREAD_MUTEX_INITIALIZER as follows. This first example is for a single mutex.

		\code
		// global variable
		pthread_mutex_t data_mutex = PTHREAD_MUTEX_INITIALIZER;
		\endcode

		Here is an example of allocating a dynamic array of mutexes
		\code
		row_mutexes = malloc(bin_length * sizeof(pthread_mutex_t));
		for (int i=0; i\<bin_length; i++)	{
			pthread_mutex_init ( &(row_mutexes[i]), NULL );
		}
		\endcode

		The mutexes are used in the same way as the other examples, with \a pthread_mutex_lock
		and \a pthread_mutex_unlock. <b>Don't forget to unlock mutexes.</b>

	\note 64-bit compatibile and tested

	\note A valuable tool with this library is to get timing information using \a clock_gettime().

	\warning
		The variadic funcitons (::create_thread and ::create_threads) contain no way to check
		the number of parameters. Consequently big problems will likely result if the
		number of paramameters, \a num_params, specified is different then the total number
		of parameters actually passed. Therefore, it is recomended to use one of the wrapping
		functions such as create_threads3() or create_thread2(), which will create an error if
		a different number of items are passed. Unfortunately this cannot check the function that
		it passed, only ensure that create_threads is called.
	\warning
		FFTW is not thread safe, however the fft_utils.c library is. Our internal library avoids
		this by locking a mutex. For more information see ::_fftw_mutex in fft_utils.c.
	\warning
		Do not use the standard \a pthread_exit function inside the spawned threads. This is
		picked up inside the framework. Just merely return the value (if any) that is to be
		passed to the \a pthread_join or ::wait_thread functions.
	\warning
		Really old versions of libc were not thread safe, and would therefore require a mutex to
		run safely. If you need this you would also need to add mutexes to all of the mallocs in
		this file.

	\todo create a seperate threads.h file to use for inclusion

	Copyright 2009 Ken Johnson
	This code is released under the terms of the GNU General Public License (GPL).
	see gpl.txt for more information.
**/

#ifndef THREADS_C
#define THREADS_C


#ifdef __cplusplus		// this makes it possible to use the library in cpp code
extern "C"
{
#endif	// __cplusplus

#include <stdlib.h>
#include <stdio.h>
#include <pthread.h>
#include <string.h>  // for memcpy
#include <stdarg.h>  // for variadic functions

/**
	\brief A standard mutex for printing to stdout.

	This defaults to the number of switch cases. For an arbitrary maximum, assembly code is
	required and can be enabled using \a THREADS_USE_ASSEMBLY. If this feature is enabled
	care must be taken as compiler flags and architecture can break va_func_caller().
 **/
pthread_mutex_t print_mutex = PTHREAD_MUTEX_INITIALIZER;

#ifndef DOXYGEN_IGNORE
__attribute__((__deprecated__))
#endif
/**
	\brief A standard mutex for printing to stdout.

	\deprecated Only really old versions of libc contained a thread unsafe malloc, and therefore
		necessatate a mutex for malloc.

	This defaults to the number of switch cases. For an arbitrary maximum, assembly code is
	required and can be enabled using \a THREADS_USE_ASSEMBLY. If this feature is enabled
	care must be taken as compiler flags and architecture can break va_func_caller().
 **/
pthread_mutex_t malloc_mutex = PTHREAD_MUTEX_INITIALIZER;

#ifndef DEFAULT_NUM_THREADS
/**
	\brief A basic number of threads that can be commonly specified, useful when program is compiled
		on the machine that will run it.

	This is meant to be defined during compilation, to set a default number of threads. Not that
	having an 'optimal' number of threads is not a big deal, as long as there are enough. Threads
	are cheap and specifiying to many typcially won't cause a slow down (excess of several orders
	of magnitude might). Therefore a good start is the number of processors that are on that
	machine or some multiple.

	For example on a linux system this could be done in a Makefile as
	\code
	-DDEFAULT_NUM_THREADS=$(shell grep processor /proc/cpuinfo | wc -l)
	\endcode
	On an OS X machine this could be implemented as
	\code
	-DDEFAULT_NUM_THREADS=$(shell system_profiler | grep "Number Of Cores" | cut -d":" -f2 | cut -d" " -f 2)
	\endcode
	or if using a Power PC platform
	\code
	-DDEFAULT_NUM_THREADS=$(shell system_profiler | grep "Number Of CPUs" | cut -d":" -f2 | cut -d" " -f 2)
	\endcode

	For more dynamic programs, that will run on machines other than where it was compiled, it is
	recommended to instead use \a get_nprocs().
 **/
#define DEFAULT_NUM_THREADS		4
#endif

/**
	\brief The maximum number of parameters that can be used in for variadic fucntion calling.

	This defaults to the number of func* created. For an arbitrary maximum, assembly code is
	required and can be enabled using \a THREADS_USE_ASSEMBLY. If this feature is enabled
	care must be taken as compiler flags and architecture can break va_func_caller().
**/
#define THREADS_MAX_NUM_PARAMS 32

// comment out the "#define THREADS_USE_ASSEMBLY" line if there are problems
//#define THREADS_USE_ASSEMBLY
#ifndef THREADS_USE_ASSEMBLY
void* func0 (void* (*func)(), void **arg)	{
	return func();
}
void* func1 (void* (*func)(), void **arg)	{
	return ((void* (*)(void*)) func)
			(arg[0]);
}
void* func2 (void* (*func)(), void **arg)	{
	return ((void* (*)(void*,void*))func)
			(arg[0], arg[1]);
}
void* func3 (void* (*func)(), void **arg)	{
	return ((void* (*)(void*,void*,void*))func)
			(arg[0], arg[1], arg[2]);
}
void* func4 (void* (*func)(), void **arg)	{
	return ((void* (*)(void*,void*,void*,void*))func)
			(arg[0], arg[1], arg[2], arg[3]);
}
void* func5 (void* (*func)(), void **arg)	{
	return ((void* (*)(void*,void*,void*,void*,void*))func)
			(arg[0], arg[1], arg[2], arg[3], arg[4]);
}
void* func6 (void* (*func)(), void **arg)	{
	return ((void* (*)(void*,void*,void*,void*,void*,void*))func)
			(arg[0], arg[1], arg[2], arg[3], arg[4], arg[5]);
}
void* func7 (void* (*func)(), void **arg)	{
	return ((void* (*)(void*,void*,void*,void*,void*,void*,void*))func)
			(arg[0], arg[1], arg[2], arg[3], arg[4], arg[5], arg[6]);
}
void* func8 (void* (*func)(), void **arg)	{
	return ((void* (*)(void*,void*,void*,void*,void*,void*,void*,void*))func)
			(arg[0], arg[1], arg[2], arg[3], arg[4], arg[5], arg[6], arg[7]);
}
void* func9 (void* (*func)(), void **arg)	{
	return ((void* (*)(void*,void*,void*,void*,void*,void*,void*,void*,void*))func)
			(arg[0], arg[1], arg[2], arg[3], arg[4], arg[5], arg[6], arg[7], arg[8]);
}
void* func10 (void* (*func)(), void **arg)	{
	return ((void* (*)(void*,void*,void*,void*,void*,void*,void*,void*,void*,void*))func)
			(arg[0], arg[1], arg[2], arg[3], arg[4], arg[5], arg[6], arg[7], arg[8], arg[9]);
}
void* func11 (void* (*func)(), void **arg)	{
	return ((void* (*)(void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*))func)
			(arg[0], arg[1], arg[2], arg[3], arg[4], arg[5], arg[6], arg[7], arg[8], arg[9], arg[10]);
}
void* func12 (void* (*func)(), void **arg)	{
	return ((void* (*)(void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*))func)
			(arg[0], arg[1], arg[2], arg[3], arg[4], arg[5], arg[6], arg[7], arg[8], arg[9], arg[10], arg[11]);
}
void* func13 (void* (*func)(), void **arg)	{
	return ((void* (*)(void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*))func)
			(arg[0], arg[1], arg[2], arg[3], arg[4], arg[5], arg[6], arg[7], arg[8], arg[9], arg[10], arg[11], arg[12]);
}
void* func14 (void* (*func)(), void **arg)	{
	return ((void* (*)(void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*))func)
			(arg[0], arg[1], arg[2], arg[3], arg[4], arg[5], arg[6], arg[7], arg[8], arg[9], arg[10], arg[11], arg[12], arg[13]);

}
void* func15 (void* (*func)(), void **arg)	{
	return ((void* (*)(void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*,void*))func)
			(arg[0], arg[1], arg[2], arg[3], arg[4], arg[5], arg[6], arg[7], arg[8], arg[9], arg[10], arg[11], arg[12], arg[13], arg[14]);

}
void* (*const funcArray[THREADS_MAX_NUM_PARAMS+1]) (void* (*func)(), void **arg) =	{
	func0,
	func1,
	func2,
	func3,
	func4,
	func5,
	func6,
	func7,
	func8,
	func9,
	func10,
	func11,
	func12,
	func13,
	func14,
	func15
};
#endif // THREADS_USE_ASSEMBLY

/**
	\brief This function exists only to be able to call the real function with an arbitrary number of parameters.

	The difficulty of the whole implementation is being able to call a function which can have
	an arbitrary number parameters. The simple solution is to branch, and provide a call for
	any number of parameters. This was implemented as the large switch here. It has been
	replaced by using an array of function pointers. Either approach limits the user to the
	number of parameters hardcoded. This is much simpler to understand and implement and
	it is possibly more robust to optimzation flags and differing architectures.

	The ideal solution is to implement it in assembly. Assembly solution doesn't limit the number
	of parameters, or slow the program down. It is fast and an ultra-trimmed piece of code. Note
	that the minimal usage of assembly is used here (in fact it is only 2 lines of asm for 32-bit).
	This won't work by default on 64-bit architecture as the frame pointer is ommited, and that
	the first parameters aren't pushed onto the stack, but rather uses registers (I guess a slight
	speed boost).

	\param num_params The number of parameters passed to \a func(). Valid values are from 0 to
		THREADS_MAX_NUM_PARAMS. This must be equivalent to the size of the array that \a arg points
		too.

	\param func The pointer to the function that will be called. This function can take an arbitrary
		number of parameters (with a minimum of zero) and must match \a num_params. Each paramter
		must be a pointer, but can be a pointer of any type.

	\param arg Array of parameters passed to \a func(). Each value must be a pointer.
		This array must contain the same number of parameters as \a num_params indicates.

	\return The return value (if any) of the passed function. If no return value is specied by
		the function, then the value returned is undefined, which is harmless if you don't use it.
**/
void *va_func_caller (long num_params, void* (*func)(), void **arg) {
	assert (num_params >= 0);
	assert (func != NULL);
	if (num_params >= 1)	{
		assert (arg != NULL);
	}

#ifndef THREADS_USE_ASSEMBLY
	// non-assembly code (for any architecture)
	return funcArray[num_params](func, arg);

#else // THREADS_USE_ASSEMBLY
#undef THREADS_MAX_NUM_PARAMS
#define THREADS_MAX_NUM_PARAMS		1024  // really can be bigger but 1k seems good
	long i;
	void *a;

	// 32-bit code (for x86 arch)

	// push the parameters on the stack (starting with the last one)
	// This system doesn't work when frame pointers (%ebp) are ommited (ie -fomit-frame-pointers)
	// as all variables are referenced directly as an offset of the stack pointer. The
	// pushl will of course modify the stack pointer (%esp) shifting all variables as well.
	for (i=num_params-1; i>=0; i--)	{
		a = arg[i];
		asm ("pushl	%[in]" : : [in] "m" (a)); // push a
	}

	a = func();

	// fix the stack
	for (i=num_params; i>0; i--)	{
		asm ("popl	%%eax" : : : "eax");
	}

	return a;

	// If arg was in reverse order, the whole va_func_caller could be
	// void *a;
	// unsigned long stack_back;
	// asm (movq %esp stack_back
	//		movq arg %esp
	//		call func
	//		movq %eax a
	//		movq stack_back %esp);
	// return a;

#endif // THREADS_USE_ASSEMBLY
}
/**
	\brief The thread wrapper, passed to pthread_create, and calls the variadic function.

	\param arg An array that contains the number of parameters, funciton pointer and parameter
		list. This array is deleted after calling the function.

	\return The return value (if any) of the passed function.
**/
void *thread_wrapper (void **arg) {
	long i;
	void *ret_val;
	assert (arg != NULL);

	if ((long) arg[0] > 0)
		ret_val = va_func_caller ((long) arg[0], (void* (*)())arg[1], &(arg[2]));
	else
		ret_val = va_func_caller ((long) arg[0], (void* (*)())arg[1], NULL);

	// delete the input array, reseting the elements first
	for (i=0; i<(long) arg[0]; i++)	{
		arg[i] = NULL;
	}
	free(arg);
	arg = NULL;

	//pthread_exit(ret_val);
	return ret_val; // same as pthread_exit(ret_val);
}
/**
	\brief Replacement for pthread_create(), which will allow an arbitrary number of
	parameters to be passed to the task function.

	Will spawn a thread which will call \a start_routine, passing the additional parameters
	to it. Just as pthread_create(), the attributes can be specified using \a attr, or
	unspecified using \c NULL.

	\param thread The thread id is set in this pointer.

	\param attr The attributes set to pass to the spawned thread. See the documentation for
		\a pthread_create() for more information.

	\param start_routine The pointer to the function that will be called for each thread. This function
		must return \c void. This function can take an arbitrary number of parameters (with a
		minimum of zero) and must match \a num_params. Each paramter must be a pointer, but can
		be a pointer of any type. Additionally \a start_routine() must not call \a pthread_exit(). See
		the documentation for \a pthread_create() for more information.

	\param num_params The number of parameters passed to \a start_routine(). Valid values are from 0 to
		THREADS_MAX_NUM_PARAMS. This must be equivalent to the number of parameters that follow
		\a num_params.

	\param ... List of parameters passed to the \a start_routine(). Each value must be a pointer.
		This must contain the same number of parameters as \a num_params indicates. The objects that
		the pointers refer to are not copied, only the reference. Therefore do not delete those objects
		until the thread completes.

	\return An error code. The value 0 is returned upon success. See the documentation for
		\a pthread_create() for more information.
 **/
int pthread_create_va (pthread_t * thread, const pthread_attr_t * attr, void *(*start_routine)(), long num_params, ...)	{
	void **params = NULL;
	assert (num_params >= 0);
	assert (num_params <= THREADS_MAX_NUM_PARAMS);
	assert (sizeof(long) == sizeof(void *));

	// set up the params array
	// note that the first two elements are num_params and the function pointer
	// also note that it is to be deleted in the thread_wrapper
	params = (void **) malloc ((num_params+2) * sizeof(void *));
	assert (params != NULL);
	params[0] = (void *) num_params;
	params[1] = (void *) start_routine;
	// start popin params
	va_list param_list;
	va_start (param_list, num_params);
	for (int i=2; i<num_params+2; i++)	{
		params[i] = va_arg (param_list, void *);
	}
	va_end (param_list);

	int ret_val = pthread_create(thread, attr, (void *(*)(void *))thread_wrapper, params);
	params = NULL; // don't worry thread_wrapper will delete the array
	return ret_val;
}
/**
	\brief Creates a thread which will run \a func(), passing to \a func() the additional parameters.

	Each invocation of create_thread() or \a create_thread[0-8]() will require a subsequent call
	to wait_thread(), or \a pthread_join(), to ensure that the thread executes.

	As with all of the end functions used in the library, the task that is passed, \a func,
	must not call \a pthread_exit(), but merely return in a typical fashion. Use care, as with
	all functions that implement a variable number of parameters, as undefined behavior will
	result if the number of parameters passed does not match \a num_params.

	\param func The pointer to the function that will be called for each thread. This function
		must return \c void. This function can take an arbitrary number of parameters (with a
		minimum of zero) and must match \a num_params. Each paramter must be a pointer, but can
		be a pointer of any type. Additionally \a func() must not call \a pthread_exit().

	\param num_params The number of parameters passed to \a func(). Valid values are from 0 to
		THREADS_MAX_NUM_PARAMS. This must be equivalent to the number of parameters that follow
		\a num_params.

	\param ... List of parameters passed to the \a func(). Each value must be a pointer. This must
		contain the same number of parameters as \a num_params indicates. The objects that the pointers
		refer to are not copied, only the reference. Therefore do not delete those objects until the
		thread completes.

	\return An error code. The value 0 is returned upon success.
**/
pthread_t create_thread (void* (*func)(), long num_params, ...)	{
	void **params = NULL;
	assert (num_params >= 0);
	assert (num_params <= THREADS_MAX_NUM_PARAMS);
	assert (sizeof(long) == sizeof(void *));

	// set up the params array
	// note that the first two elements are num_params and the function pointer
	// also note that it is to be deleted in the thread_wrapper
	params = (void **) malloc ((num_params+2) * sizeof(void *));
	assert (params != NULL);
	params[0] = (void *) num_params;
	params[1] = (void *) func;
	// start popin params
	va_list param_list;
	va_start (param_list, num_params);
	for (int i=2; i<num_params+2; i++)	{
		params[i] = va_arg (param_list, void *);
	}
	va_end (param_list);

	pthread_t thread_id;
	int rc = pthread_create(&thread_id, NULL, (void *(*)(void *))thread_wrapper, params);
	if (rc != 0) printf("ERROR: create_thread() failed. threads.c:%d\n", __LINE__);
    assert (rc == 0);
	params = NULL; // don't worry thread_wrapper will delete the array

	return thread_id;
}
/**
	\brief Called to wait on a specific thread, for use in conjunction with create_thread().

	This function will wait for the specified thread to finish and return control to the calling
	code. This simply calls pthread_join().

	\param thread_id The identifier of the thread that is waited on.

	\return The value returned, if any, by the returned thread.
 **/
void *wait_thread (pthread_t thread_id)	{
	void *ret_val;
	int rc = pthread_join(thread_id, &ret_val);
	if (rc != 0) printf("ERROR: create_thread() failed. threads.c:%d\n", __LINE__);
	assert (rc == 0);
	return ret_val;
}
/**
	\brief Creates a set of threads, each of which will run \a func(), passing to \a func()
	the current thread number and the total number of threads as well as the additional parameters.

	This function will initiate the threads and wait until all threads finish before control is
	returned to the code that calls create_threads().

	Use care, as with all functions that implement a variable number of parameters, as undefined
	behavior will result if the number of parameters passed does not match \a num_params. Consequently
	this function is also implemented in a more type safe form as

	\param num_threads The number of threads that will be spawned by create_threads().

	\param func The pointer to the function that will be called for each thread. This function
		must return \c void. This function can take an arbitrary number of parameters (with a
		minimum of two) and must match \a num_params + 2. The first pointer passed to \a func() must
		be <tt>int *cur_thread</tt> which will point to a value from 0 to \a num_threads - 1. The
		second paramter passed to \a func() must be <tt>int *num_threads</tt> which will point to
		a value equal to \a num_threads. Each additional paramter must be a pointer, but can be a pointer
		of any type. Additionally \a func() must not call \a pthread_exit().

	\param num_params The number of extra parameters passed to \a func(). Valid values are from 0 to
		THREADS_MAX_NUM_PARAMS - 2. This must be equivalent to the number of parameters that
		follow \a num_params.

	\param ... List of additional parameters passed to each of the threads. Each value
		must be a pointer. This must contain the same number of parameters as \a num_params
		indicates.

	\return An error code. The value 0 is returned upon success.
 **/
int create_threads (int num_threads, void (*func)(), long num_params, ...)	{
	assert (num_threads > 0);
	assert (num_params >= 0);
	assert (num_params <= THREADS_MAX_NUM_PARAMS);
	assert (sizeof(long) == sizeof(void *));

	// this array is to hold the thread ids
	pthread_t *threads_id = NULL;
	threads_id = (pthread_t *) malloc (num_threads * sizeof(pthread_t) );
	assert (threads_id != NULL);

	// this array is to hold the index of the current thread
	int *cur_thread_array = NULL;
	cur_thread_array = (int *) malloc (num_threads * sizeof(int));
	assert (cur_thread_array != NULL);

	// set up the basic params array (will be copied for each thread)
	// note that the first two elements are num_params and the function pointer
	long act_num_params = num_params + 2;
	long total_params = act_num_params + 4;
	assert (num_params >= 0);
	assert (act_num_params <= THREADS_MAX_NUM_PARAMS);
	void **params_master = NULL;
	params_master = (void **) malloc (total_params * sizeof(void **));
	assert (params_master != NULL);
	params_master[0] = (void *) act_num_params;
	params_master[1] = (void *) func;
	params_master[2] = &num_threads;
	params_master[3] = NULL;
	va_list param_list;
	va_start (param_list, num_params);
	for (int i=4; i<num_params+4; i++)	{
		params_master[i] = va_arg (param_list, void *);
	}
	va_end (param_list);

	// set up the array of copies
	void ***params = NULL;
	params = (void ***) malloc (num_threads * sizeof(void **));
	assert (params != NULL);

	// create and run threads
	for(int t=0; t<num_threads; t++)	{
		// copy the master copy and set individual parameter
		cur_thread_array[t] = t;
		// note that each params[t] is to be deleted in the thread_wrapper
		params[t] = (void **) malloc (total_params * sizeof(void **));
		assert (params[t] != NULL);
		memcpy (params[t], params_master, total_params*sizeof(void **));
		params[t][3] = &(cur_thread_array[t]);

		// create this thread
		int rc = pthread_create(&(threads_id[t]), NULL, (void *(*)(void *))thread_wrapper, params[t]);
    	if (rc != 0) printf("ERROR: create_threads() failed. threads.c:%d\n", __LINE__);
		assert (rc == 0);
		params[t] = NULL; // don't worry thread_wrapper will delete the array
	}

	// wait for threads to finish (ie join)
	for(int t=0; t<num_threads; t++)	{
		wait_thread (threads_id[t]);
	}

	// cleanup
	free(params);
	params = NULL;
	free (cur_thread_array);
	cur_thread_array = NULL;
	free (threads_id);
	threads_id = NULL;
	free(params_master);
	params_master = NULL;

	return 0;
}

/**
    Helper function to divide the number of jobs as evenly as possible among
    worker threads.

    get_start() and get_stop() can be used to conveniently get the start and
    stop indices for looping over jobs within a given thread.
**/
uint64_t get_start(int num_threads, int cur_thread, int num_jobs) {
    if(cur_thread > num_jobs) return -1;

    int elements_per_chunk = num_jobs / num_threads;
    int extra_jobs = num_jobs % num_threads;
    uint64_t start = elements_per_chunk * cur_thread;
    if(cur_thread < extra_jobs)
    {
        start += cur_thread;
    } else
    {
        start += extra_jobs;
    }
    return start;
}

/**
    Helper function to divide the number of jobs as evenly as possible among
    worker threads.

    get_start() and get_stop() can be used to conveniently get the start and
    stop indices for looping over jobs within a given thread.
**/
uint64_t get_stop(int num_threads, int cur_thread, int num_jobs) {
    if(cur_thread > num_jobs) return -1;

    int elements_per_chunk = num_jobs / num_threads;
    int extra_jobs = num_jobs % num_threads;
    uint64_t stop = get_start(num_threads, cur_thread, num_jobs);
    stop += elements_per_chunk;
    if(cur_thread < extra_jobs)
    {
        stop++;
    }
    return stop;
}

/**
	Print the current progress and ETA of the threaded function.

	The \em num_threads must always be constant, as it is used
	to create an array and access it.

	\todo fix it to be able to reset the progress bar
**/
void printProgress (int num_threads, int cur_thread, double percent)	{
	struct timespec ttime;

	static double c0 = -1000;
	static double cprev = -1000;
	static double *cthread = NULL; // this array stores the percent from every thread
	static double prev_bs = 0;
	static int pmini = 0;

    /* NRZ: set to unrealistic value until an adequate-mulit-platform solution can be
     * found to replace clock_gettime()
     */
    ttime.tv_sec = -1;
    ttime.tv_nsec = -1;

	// this mutex eliminates simultaneous printf deals and array access
	pthread_mutex_lock( &print_mutex );

	// these lines only execute the very first time the function is run
	if (c0 == -1000)	{
		assert (num_threads > 0);
		assert (cthread == NULL);

        /* NRZ: clock_gettime() requires librt which is not available on other platforms */
		//clock_gettime (CLOCK_MONOTONIC, &ttime);

		c0 = ttime.tv_sec + 0.000000001 * (unsigned long) ttime.tv_nsec;
		cprev = c0;
		cthread = (double *) calloc ((num_threads+1), sizeof(double) ); // the extra +1 will help us varify that the same num_threads is always passed
		cthread[0] = num_threads;
	}

	assert (cthread != NULL);
	assert (num_threads == cthread[0]);
	assert (cur_thread < num_threads && cur_thread >= 0);
	cthread[cur_thread+1] = percent;

	// get timing information (total run time and time since prev print)
    /* NRZ: clock_gettime() requires librt which is not available on other platforms */
	//clock_gettime (CLOCK_MONOTONIC, &ttime);
	double ctime = ttime.tv_sec + 0.000000001 * (unsigned long) ttime.tv_nsec;
	// return if previous print was too recent
	// also return if this is not the previous minimum - this improves accuracy alot
	if (ctime - cprev < 0.5 || cur_thread != pmini)	{
		pthread_mutex_unlock (&print_mutex);
		return;
	}
	double time = ctime - c0;
	assert (time >= 0);
	assert (cprev > 0.0);

	// set min max and mean
	double min = 10000000.0, max = 0.0, mean = 0.0;
	int mini = 0;
	for (int i=0; i<num_threads; i++)	{
		double cur = cthread[i+1];
		mean += cur;
		if (cur < min)	{
			min = cur;
			mini = i;
		}
		else if (cur > max)	{
			max = cur;
		}
	}
	mean /= num_threads;
	assert (mean >= 0);

	if (min == 0.0)	{
		cprev = ctime;
		pmini = mini;
		pthread_mutex_unlock (&print_mutex);
		return;
	}

	// sets the ETA stuff
	double big_sec = time/(min/100.0); /// CHANGE ONLY THIS, TO USE PART INSTEAD OF PERCENT
	if (big_sec < 0)
		big_sec = 0;
	// the next two lines do a first order difference filter
	double a = 0.25;
	big_sec = a * big_sec + (1.0-a)*prev_bs;
	int hour = (int) ( (big_sec-time)/3600 );
	int minut = (int) (fmod ((big_sec-time), 3600) / 60);
	int sec = (int) (fmod ((big_sec-time), 60));

	// print it all out
	printf ("%8.1fs  ETA:%6ds (%d:%02d:%02d)  mean:%2.4f  min(%d):%2.3f  max:%2.3f  estTot:%9ds     \r", time, (int)(big_sec-time), hour, minut, sec, mean, mini, min, max, (int)(big_sec));
	fflush(stdout);

	cprev = ctime;
	prev_bs = big_sec;
	pmini = mini;

	// never forget to unlock mutexes
	pthread_mutex_unlock (&print_mutex);
}

#ifndef __cplusplus
pthread_t create_thread0 (void* (*func)())	{
	return create_thread (func, 0);
}
pthread_t create_thread1 (void* (*func)(), void *a)	{
	return create_thread (func, 1, a);
}
pthread_t create_thread2 (void* (*func)(), void *a, void *b)	{
	return create_thread (func, 2, a, b);
}
pthread_t create_thread3 (void* (*func)(), void *a, void *b, void *c)	{
	return create_thread (func, 3, a, b, c);
}
pthread_t create_thread4 (void* (*func)(), void *a, void *b, void *c, void *d)	{
	return create_thread (func, 4, a, b, c, d);
}
pthread_t create_thread5 (void* (*func)(), void *a, void *b, void *c, void *d, void *e)	{
	return create_thread (func, 5, a, b, c, d, e);
}
pthread_t create_thread6 (void* (*func)(), void *a, void *b, void *c, void *d, void *e, void *f)	{
	return create_thread (func, 6, a, b, c, d, e, f);
}
pthread_t create_thread7 (void* (*func)(), void *a, void *b, void *c, void *d, void *e, void *f, void *g)	{
	return create_thread (func, 7, a, b, c, d, e, f, g);
}
pthread_t create_thread8 (void* (*func)(), void *a, void *b, void *c, void *d, void *e, void *f, void *g, void *h)	{
	return create_thread (func, 8, a, b, c, d, e, f, g, h);
}
pthread_t create_thread9 (void* (*func)(), void *a, void *b, void *c, void *d, void *e, void *f, void *g, void *h, void *i)	{
	return create_thread (func, 9, a, b, c, d, e, f, g, h, i);
}
int create_threads0 (int num_threads, void (*func)())	{
	return create_threads (num_threads, func, 0);
}
int create_threads1 (int num_threads, void (*func)(), void *a)	{
	return create_threads (num_threads, func, 1, a);
}
int create_threads2 (int num_threads, void (*func)(), void *a, void *b)	{
	return create_threads (num_threads, func, 2, a, b);
}
int create_threads3 (int num_threads, void (*func)(), void *a, void *b, void *c)	{
	return create_threads (num_threads, func, 3, a, b, c);
}
int create_threads4 (int num_threads, void (*func)(), void *a, void *b, void *c, void *d)	{
	return create_threads (num_threads, func, 4, a, b, c, d);
}
int create_threads5 (int num_threads, void (*func)(), void *a, void *b, void *c, void *d, void *e)	{
	return create_threads (num_threads, func, 5, a, b, c, d, e);
}
int create_threads6 (int num_threads, void (*func)(), void *a, void *b, void *c, void *d, void *e, void *f)	{
	return create_threads (num_threads, func, 6, a, b, c, d, e, f);
}
int create_threads7 (int num_threads, void (*func)(), void *a, void *b, void *c, void *d, void *e, void *f, void *g)	{
	return create_threads (num_threads, func, 7, a, b, c, d, e, f, g);
}
int create_threads8 (int num_threads, void (*func)(), void *a, void *b, void *c, void *d, void *e, void *f, void *g, void *h)	{
	return create_threads (num_threads, func, 8, a, b, c, d, e, f, g, h);
}
int create_threads9 (int num_threads, void (*func)(), void *a, void *b, void *c, void *d, void *e, void *f, void *g, void *h, void *i)	{
	return create_threads (num_threads, func, 9, a, b, c, d, e, f, g, h, i);
}
int create_threads10 (int num_threads, void (*func)(), void *a, void *b, void *c, void *d, void *e, void *f, void *g, void *h, void *i, void *j)	{
	return create_threads (num_threads, func, 10, a, b, c, d, e, f, g, h, i, j);
}
int create_threads11 (int num_threads, void (*func)(), void *a, void *b, void *c, void *d, void *e, void *f, void *g, void *h, void *i, void *j, void *k)	{
	return create_threads (num_threads, func, 11, a, b, c, d, e, f, g, h, i, j, k);
}
int create_threads12 (int num_threads, void (*func)(), void *a, void *b, void *c, void *d, void *e, void *f, void *g, void *h, void *i, void *j, void *k, void *l)	{
	return create_threads (num_threads, func, 12, a, b, c, d, e, f, g, h, i, j, k, l);
}
int create_threads13 (int num_threads, void (*func)(), void *a, void *b, void *c, void *d, void *e, void *f, void *g, void *h, void *i, void *j, void *k, void *l, void *m)	{
	return create_threads (num_threads, func, 13, a, b, c, d, e, f, g, h, i, j, k, l, m);
}
#else // __cplusplus
}
// Function pointers will not get automatically cast in C++. Therefore some casting is required
// While oneline functions could be made as above, a recasting macro would still be required for the
// function pointer. It can be done in one easy sweep with the following, when everything is recast.
// static_cast will only be able to recast pointers as pointers, therefore ensuring pointers passed.
// reinterpret_cast will recast anything, so use with care.
#define rcv reinterpret_cast<void*(*)()>
#define _s static_cast<void*>
#define create_thread0(__fu) \
			create_thread(rcv(__fu),0)
#define create_thread1(__fu,_a) \
			create_thread(rcv(__fu),1,_s(_a))
#define create_thread2(__fu,_a,_b) \
			create_thread(rcv(__fu),2,_s(_a),_s(_b))
#define create_thread3(__fu,_a,_b,_c) \
			create_thread(rcv(__fu),3,_s(_a),_s(_b),_s(_c))
#define create_thread4(__fu,_a,_b,_c,_d) \
			create_thread(rcv(__fu),4,_s(_a),_s(_b),_s(_c),_s(_d))
#define create_thread5(__fu,_a,_b,_c,_d,_e) \
			create_thread(rcv(__fu),5,_s(_a),_s(_b),_s(_c),_s(_d),_s(_e))
#define create_thread6(__fu,_a,_b,_c,_d,_e,_f) \
			create_thread(rcv(__fu),6,_s(_a),_s(_b),_s(_c),_s(_d),_s(_e),_s(_f))
#define create_thread7(__fu,_a,_b,_c,_d,_e,_f,_g) \
			create_thread(rcv(__fu),7,_s(_a),_s(_b),_s(_c),_s(_d),_s(_e),_s(_f),_s(_g))
#define create_thread8(__fu,_a,_b,_c,_d,_e,_f,_g,_h) \
			create_thread(rcv(__fu),8,_s(_a),_s(_b),_s(_c),_s(_d),_s(_e),_s(_f),_s(_g),_s(_h))
#define create_thread9(__fu,_a,_b,_c,_d,_e,_f,_g,_h,_i) \
			create_thread(rcv(__fu),9,_s(_a),_s(_b),_s(_c),_s(_d),_s(_e),_s(_f),_s(_g),_s(_h),_s(_i))
#define create_thread10(__fu,_a,_b,_c,_d,_e,_f,_g,_h,_i,_j) \
			create_thread(rcv(__fu),10,_s(_a),_s(_b),_s(_c),_s(_d),_s(_e),_s(_f),_s(_g),_s(_h),_s(_i),_s(_j))
// #undef rcv
#define rcvv reinterpret_cast<void(*)()>
#define create_threads0(__nt,__fu) \
			create_threads(__nt,rcvv(__fu),0)
#define create_threads1(__nt,__fu,_a) \
			create_threads(__nt,rcvv(__fu),1,_a)
#define create_threads2(__nt,__fu,_a,_b) \
			create_threads(__nt,rcvv(__fu),2,_a,_b)
#define create_threads3(__nt,__fu,_a,_b,_c) \
			create_threads(__nt,rcvv(__fu),3,_a,_b,_c)
#define create_threads4(__nt,__fu,_a,_b,_c,_d) \
			create_threads(__nt,rcvv(__fu),4,_a,_b,_c,_d)
#define create_threads5(__nt,__fu,_a,_b,_c,_d,_e) \
			create_threads(__nt,rcvv(__fu),5,_a,_b,_c,_d,_e)
#define create_threads6(__nt,__fu,_a,_b,_c,_d,_e,_f) \
			create_threads(__nt,rcvv(__fu),6,_a,_b,_c,_d,_e,_f)
#define create_threads7(__nt,__fu,_a,_b,_c,_d,_e,_f,_g) \
			create_threads(__nt,rcvv(__fu),7,_a,_b,_c,_d,_e,_f,_g)
#define create_threads8(__nt,__fu,_a,_b,_c,_d,_e,_f,_g,_h) \
			create_threads(__nt,rcvv(__fu),8,_a,_b,_c,_d,_e,_f,_g,_h)
#define create_threads9(__nt,__fu,_a,_b,_c,_d,_e,_f,_g,_h,_i) \
			create_threads(__nt,rcvv(__fu),9,_a,_b,_c,_d,_e,_f,_g,_h,_i)
#define create_threads10(__nt,__fu,_a,_b,_c,_d,_e,_f,_g,_h,_i,_j) \
			create_threads(__nt,rcvv(__fu),10,_a,_b,_c,_d,_e,_f,_g,_h,_i,_j)
#define create_threads11(__nt,__fu,_a,_b,_c,_d,_e,_f,_g,_h,_i,_j,_k) \
			create_threads(__nt,rcvv(__fu),11,_a,_b,_c,_d,_e,_f,_g,_h,_i,_j,_k)
#define create_threads12(__nt,__fu,_a,_b,_c,_d,_e,_f,_g,_h,_i,_j,_k,_l) \
			create_threads(__nt,rcvv(__fu),12,_a,_b,_c,_d,_e,_f,_g,_h,_i,_j,_k,_l)
#define create_threads13(__nt,__fu,_a,_b,_c,_d,_e,_f,_g,_h,_i,_j,_k,_l,_m) \
			create_threads(__nt,rcvv(__fu),13,_a,_b,_c,_d,_e,_f,_g,_h,_i,_j,_k,_l,_m)


#endif // __cplusplus

#endif
// THREADS_C

