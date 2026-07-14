# Host build of the pure-C metrology core + its tests. No hardware/HAL.
CC      ?= cc
CFLAGS  ?= -std=c11 -Wall -Wextra -O2
LDLIBS  := -lm

test_metrology: test_metrology.c ../app/metrology.c
	$(CC) $(CFLAGS) -o $@ $^ $(LDLIBS)

.PHONY: check clean
check: test_metrology
	./test_metrology

clean:
	rm -f test_metrology
