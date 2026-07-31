# OpenGoodixSPI Driver Makefile

KERNEL_VERSION := $(shell uname -r)
KERNEL_DIR := /lib/modules/$(KERNEL_VERSION)/build
MODULE_NAME := opengoodixspi

obj-m += $(MODULE_NAME).o

$(MODULE_NAME)-objs := opengoodixspi.o

ccflags-y := -I$(src) -Wall -Wextra

all: modules

modules:
	$(MAKE) -C $(KERNEL_DIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KERNEL_DIR) M=$(PWD) clean
	rm -f *.o *.ko *.mod.c modules.order Module.symvers

load: modules
	sudo rmmod $(MODULE_NAME) 2>/dev/null || true
	sudo insmod ./$(MODULE_NAME).ko

unload:
	sudo rmmod $(MODULE_NAME) 2>/dev/null || true

sign:
	@if [ -f "/usr/src/linux-headers-$(KERNEL_VERSION)/scripts/sign-file" ]; then \
		sudo /usr/src/linux-headers-$(KERNEL_VERSION)/scripts/sign-file sha256 /path/to/your/signing_key.priv /path/to/your/signing_key.x509 $(MODULE_NAME).ko; \
		echo "Module signed (update paths if needed)."; \
	else \
		echo "Signing tools not found. Secure Boot may require manual signing."; \
	fi

# DKMS support
dkms-install:
	sudo mkdir -p /usr/src/$(MODULE_NAME)-0.1.0
	sudo cp -r . /usr/src/$(MODULE_NAME)-0.1.0/
	sudo dkms add -m $(MODULE_NAME) -v 0.1.0
	sudo dkms build -m $(MODULE_NAME) -v 0.1.0
	sudo dkms install -m $(MODULE_NAME) -v 0.1.0

dkms-remove:
	sudo dkms remove -m $(MODULE_NAME) -v 0.1.0 --all || true
	sudo rm -rf /usr/src/$(MODULE_NAME)-0.1.0

.PHONY: all modules clean load unload sign dkms-install dkms-remove