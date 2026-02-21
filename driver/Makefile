# Makefile for OpenGoodixSPI

obj-m += opengoodixspi.o

KERNEL_DIR ?= /lib/modules/$(shell uname -r)/build
PWD := $(shell pwd)

all:
	$(MAKE) -C $(KERNEL_DIR) M=$(PWD) modules

sign: all
	$(KERNEL_DIR)/scripts/sign-file sha256 ../MOK.priv ../MOK.der opengoodixspi.ko

clean:
	$(MAKE) -C $(KERNEL_DIR) M=$(PWD) clean