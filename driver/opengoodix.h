/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __OPENGOODIX_H
#define __OPENGOODIX_H

/*
 * IOCTL commands for the OpenGoodixSPI driver
 */

#define GOODIX_IOC_MAGIC 'G'

/* Get the current state of the driver engine. */
#define GOODIX_IOC_GET_STATE _IOR(GOODIX_IOC_MAGIC, 1, int)

/* Force a software reset of the device. */
#define GOODIX_IOC_RESET     _IO(GOODIX_IOC_MAGIC, 2)

#endif /* __OPENGOODIX_H */