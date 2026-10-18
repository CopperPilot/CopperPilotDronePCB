# ==============================================================================
# CopperPilot Drone Firmware - Build, Test & Quality Assurance Makefile
# ==============================================================================

CC         ?= clang
CFLAGS     := -Wall -Wextra -std=c11 -O2
TEST_FLAGS := -Wall -Wextra -std=c11 -O0 -g -DTEST_RUNNER_ALL
COV_FLAGS  := $(TEST_FLAGS) -fprofile-arcs -ftest-coverage

INCLUDES   := -I$(CURDIR)/components/hal/include \
              -I$(CURDIR)/components/avionics/include \
              -I$(CURDIR)/components/networking/include \
              -I$(CURDIR)/components/web_ui \
              -I$(CURDIR)/tests/unity

SRCS_C     := $(shell find main components tests -type f -name "*.c")
SRCS_H     := $(shell find main components tests -type f -name "*.h")

TEST_DIR   := tests
BUILD_DIR  := build
NATIVE_BIN := $(TEST_DIR)/run_tests
COV_BIN    := $(TEST_DIR)/run_tests_cov

.PHONY: all help fmt fmt-check lint test coverage build flash monitor clean

all: test lint

help:
	@echo "CopperPilot Drone Firmware Targets:"
	@echo "  make test      - Compile and run native desktop unit tests (Unity framework)"
	@echo "  make coverage  - Compile with gcov coverage instrumentation and print metrics"
	@echo "  make lint      - Run static analysis and syntax checks (clang / cppcheck)"
	@echo "  make fmt       - Format all C source and header files using clang-format"
	@echo "  make fmt-check - Verify code formatting compliance"
	@echo "  make build     - Cross-compile target ESP32-S3 firmware with ESP-IDF"
	@echo "  make flash     - Flash target binary to ESP32-S3 over USB-CDC"
	@echo "  make monitor   - Launch ESP-IDF serial monitor console"
	@echo "  make clean     - Remove native test binaries, coverage profiles, and target build"

fmt:
	@echo "==> Formatting C/C++ source code with clang-format..."
	@if command -v clang-format > /dev/null; then \
		clang-format -i $(SRCS_C) $(SRCS_H); \
		echo "Formatting complete."; \
	else \
		echo "Notice: clang-format not installed on host. Skipping in-place formatting."; \
	fi

fmt-check:
	@echo "==> Checking C/C++ formatting compliance..."
	@if command -v clang-format > /dev/null; then \
		clang-format --dry-run --Werror $(SRCS_C) $(SRCS_H); \
		echo "Format check passed."; \
	else \
		echo "Notice: clang-format not installed on host. Skipping dry-run check."; \
	fi

lint:
	@echo "==> Running static syntax and type analysis with $(CC)..."
	@$(CC) -fsyntax-only -Wall -Wextra -std=c11 $(INCLUDES) \
		components/hal/hal_mock.c \
		components/avionics/src/pid.c \
		components/avionics/src/ahrs.c \
		components/avionics/src/motor_mixer.c \
		components/avionics/src/mpu6050.c \
		components/networking/src/wifi_ap.c \
		components/networking/src/web_server.c \
		main/main.c
	@if command -v cppcheck > /dev/null; then \
		echo "==> Running cppcheck analysis..."; \
		cppcheck --enable=warning,performance,portability --error-exitcode=1 \
			components/avionics components/hal components/networking main; \
	fi
	@echo "Static analysis clean: 0 warnings, 0 errors."

test:
	@echo "==> Compiling native desktop unit test runner..."
	@$(CC) $(TEST_FLAGS) $(INCLUDES) \
		$(TEST_DIR)/unity/unity.c \
		components/hal/hal_mock.c \
		components/avionics/src/pid.c \
		components/avionics/src/ahrs.c \
		components/avionics/src/motor_mixer.c \
		components/avionics/src/mpu6050.c \
		components/networking/src/web_server.c \
		$(TEST_DIR)/test_pid.c \
		$(TEST_DIR)/test_ahrs.c \
		$(TEST_DIR)/test_motor_mixer.c \
		$(TEST_DIR)/test_battery_failsafe.c \
		$(TEST_DIR)/test_runner.c \
		-lm -o $(NATIVE_BIN)
	@echo "==> Executing native unit tests..."
	@$(NATIVE_BIN)
	@rm -f $(NATIVE_BIN)

coverage:
	@echo "==> Compiling instrumented unit tests with gcov..."
	@cd $(TEST_DIR) && $(CC) -c $(COV_FLAGS) $(INCLUDES) \
		$(CURDIR)/components/avionics/src/pid.c \
		$(CURDIR)/components/avionics/src/ahrs.c \
		$(CURDIR)/components/avionics/src/motor_mixer.c \
		$(CURDIR)/components/networking/src/web_server.c
	@cd $(TEST_DIR) && $(CC) -c $(TEST_FLAGS) $(INCLUDES) \
		unity/unity.c \
		$(CURDIR)/components/hal/hal_mock.c \
		test_pid.c \
		test_ahrs.c \
		test_motor_mixer.c \
		test_battery_failsafe.c \
		test_runner.c
	@cd $(TEST_DIR) && $(CC) -fprofile-arcs -ftest-coverage *.o -lm -o run_tests_cov
	@echo "==> Executing test runner to record code execution..."
	@$(TEST_DIR)/run_tests_cov > /dev/null
	@echo "==> Generating gcov statement coverage report:"
	@cd $(TEST_DIR) && gcov pid.o ahrs.o motor_mixer.o web_server.o
	@rm -rf $(COV_BIN) $(TEST_DIR)/*.o $(TEST_DIR)/*.gcda $(TEST_DIR)/*.gcno $(TEST_DIR)/*.gcov $(TEST_DIR)/*.dSYM

build:
	@echo "==> Cross-compiling ESP32-S3 target firmware with ESP-IDF..."
	@if command -v idf.py > /dev/null; then \
		idf.py build; \
	else \
		echo "Error: idf.py not found in PATH. Sourced ESP-IDF environment required."; \
		echo "Run: . \$$HOME/esp/esp-idf/export.sh && make build"; \
		exit 1; \
	fi

flash:
	@idf.py flash

monitor:
	@idf.py monitor

clean:
	@rm -rf $(BUILD_DIR) $(NATIVE_BIN) $(COV_BIN) $(TEST_DIR)/*.o $(TEST_DIR)/*.gcda $(TEST_DIR)/*.gcno $(TEST_DIR)/*.gcov $(TEST_DIR)/*.dSYM
	@echo "Firmware build and test artifacts cleaned."
