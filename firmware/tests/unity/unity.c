/* ==========================================
    Unity Project - A Test Framework for C
    Copyright (c) 2007-21 Mike Karlesky, Mark VanderVoord, Greg Williams
    [Released under MIT License. Please refer to license.txt for details]
========================================== */

#include "unity.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

UNITY_STORAGE_T Unity;

void UnityBegin(const char *filename) {
    Unity.TestFile = filename;
    Unity.CurrentTestName = NULL;
    Unity.NumberOfTests = 0;
    Unity.TestFailures = 0;
    Unity.TestIgnores = 0;
    Unity.CurrentTestLineNumber = 0;
    printf("\n=== Unity Test Suite: %s ===\n", filename);
}

int UnityEnd(void) {
    printf("------------------------------------\n");
    printf("%u Tests, %u Failures, %u Ignored\n", Unity.NumberOfTests, Unity.TestFailures,
           Unity.TestIgnores);
    if (Unity.TestFailures == 0) {
        printf("OK - All tests passed!\n");
        return 0;
    } else {
        printf("FAIL - %u test(s) failed\n", Unity.TestFailures);
        return 1;
    }
}

void UnityDefaultTestRun(void (*func)(void), const char *name, int line_num) {
    Unity.CurrentTestName = name;
    Unity.CurrentTestLineNumber = (unsigned int)line_num;
    Unity.NumberOfTests++;

    if (TEST_PROTECT()) {
        setUp();
        func();
    }
    if (TEST_PROTECT()) {
        tearDown();
    }

    if (Unity.CurrentTestName) {
        printf("  [PASS] %s\n", name);
    }
}

int TEST_PROTECT(void) {
    return (setjmp(Unity.AbortFrame) == 0);
}

void UnityFail(const char *msg, unsigned int line) {
    printf("  [FAIL] %s (line %u): %s\n", Unity.CurrentTestName, line,
           msg ? msg : "Assertion failed");
    Unity.TestFailures++;
    Unity.CurrentTestName = NULL;
    longjmp(Unity.AbortFrame, 1);
}

void UnityAssertEqualNumber(intmax_t expected, intmax_t actual, const char *msg, unsigned int line,
                            int style) {
    (void)style;
    if (expected != actual) {
        char buf[128];
        snprintf(buf, sizeof(buf), "%s Expected %jd, but got %jd", msg ? msg : "", expected,
                 actual);
        UnityFail(buf, line);
    }
}

void UnityAssertFloatsWithin(float delta, float expected, float actual, const char *msg,
                             unsigned int line) {
    float diff = fabsf(expected - actual);
    if (diff > delta || isnan(diff)) {
        char buf[128];
        snprintf(buf, sizeof(buf), "%s Expected %f within %f, got %f", msg ? msg : "",
                 (double)expected, (double)delta, (double)actual);
        UnityFail(buf, line);
    }
}
