all:
	$(MAKE) -C driver

sign:
	$(MAKE) -C driver sign

clean:
	$(MAKE) -C driver clean

load:
	-sudo rmmod opengoodixspi
	sudo insmod driver/opengoodixspi.ko

unload:
	sudo rmmod opengoodixspi