/* ==========================================
    Unity Project - A Test Framework for C
    Copyright (c) 2007-21 Mike Karlesky, Mark VanderVoord, Greg Williams
    [Released under MIT License. Please refer to license.txt for details]
========================================== */

#ifndef UNITY_FRAMEWORK_H
#define UNITY_FRAMEWORK_H

#include "unity_internals.h"

#define TEST_ASSERT(condition)                                                                     \
    UNITY_TEST_ASSERT((condition), __LINE__, "Condition evaluated to FALSE")
#define TEST_ASSERT_TRUE(condition)                                                                \
    UNITY_TEST_ASSERT((condition), __LINE__, " Expected TRUE Was FALSE")
#define TEST_ASSERT_FALSE(condition)                                                               \
    UNITY_TEST_ASSERT(!(condition), __LINE__, " Expected FALSE Was TRUE")
#define TEST_ASSERT_EQUAL_INT(expected, actual)                                                    \
    UNITY_TEST_ASSERT_EQUAL_INT((expected), (actual), __LINE__, NULL)
#define TEST_ASSERT_EQUAL_UINT(expected, actual)                                                   \
    UNITY_TEST_ASSERT_EQUAL_INT((expected), (actual), __LINE__, NULL)
#define TEST_ASSERT_FLOAT_WITHIN(delta, exp, act)                                                  \
    UNITY_TEST_ASSERT_FLOAT_WITHIN((delta), (exp), (act), __LINE__, NULL)
#define TEST_ASSERT_NOT_NULL(pointer)                                                              \
    UNITY_TEST_ASSERT((pointer) != NULL, __LINE__, " Expected Non-NULL")
#define TEST_FAIL_MESSAGE(message) UnityFail((message), __LINE__)

#define RUN_TEST(func) UnityDefaultTestRun(func, #func, __LINE__)

void setUp(void);
void tearDown(void);

#endif
