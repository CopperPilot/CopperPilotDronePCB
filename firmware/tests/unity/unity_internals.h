/* ==========================================
    Unity Project - A Test Framework for C
    Copyright (c) 2007-21 Mike Karlesky, Mark VanderVoord, Greg Williams
    [Released under MIT License. Please refer to license.txt for details]
========================================== */

#ifndef UNITY_INTERNALS_H
#define UNITY_INTERNALS_H

#include <setjmp.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define UNITY_DISPLAY_STYLE_INT 0
#define UNITY_DISPLAY_STYLE_FLOAT 1

typedef struct UNITY_STORAGE_T {
    const char *TestFile;
    const char *CurrentTestName;
    unsigned int NumberOfTests;
    unsigned int TestFailures;
    unsigned int TestIgnores;
    unsigned int CurrentTestLineNumber;
    jmp_buf AbortFrame;
} UNITY_STORAGE_T;

extern UNITY_STORAGE_T Unity;

void UnityBegin(const char *filename);
int UnityEnd(void);
int TEST_PROTECT(void);
void UnityDefaultTestRun(void (*func)(void), const char *name, int line_num);
void UnityAssertEqualNumber(intmax_t expected, intmax_t actual, const char *msg, unsigned int line,
                            int style);
void UnityAssertFloatsWithin(float delta, float expected, float actual, const char *msg,
                             unsigned int line);
void UnityAssertTrue(int condition, const char *msg, unsigned int line);
void UnityFail(const char *msg, unsigned int line);

#define UNITY_TEST_ASSERT(condition, line, msg)                                                    \
    if (!(condition)) {                                                                            \
        UnityFail(msg, (unsigned int)(line));                                                      \
    }

#define UNITY_TEST_ASSERT_EQUAL_INT(expected, actual, line, msg)                                   \
    UnityAssertEqualNumber((intmax_t)(expected), (intmax_t)(actual), msg, (unsigned int)(line),    \
                           UNITY_DISPLAY_STYLE_INT)

#define UNITY_TEST_ASSERT_FLOAT_WITHIN(delta, expected, actual, line, msg)                         \
    UnityAssertFloatsWithin((float)(delta), (float)(expected), (float)(actual), msg,               \
                            (unsigned int)(line))

#endif
