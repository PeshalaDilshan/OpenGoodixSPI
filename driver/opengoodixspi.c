// SPDX-License-Identifier: GPL-2.0-only
/*
 * OpenGoodixSPI - Experimental Linux kernel driver for Goodix SPI fingerprint sensors
 *
 * Copyright (C) 2024 OpenGoodixSPI Contributors
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/spi/spi.h>
#include <linux/acpi.h>
#include <linux/cdev.h>
#include <linux/fs.h>
#include <linux/device.h>
#include <linux/slab.h>
#include <linux/mutex.h>
#include <linux/uaccess.h>
#include <linux/version.h>
#include <linux/interrupt.h>
#include <linux/mod_devicetable.h>
#include <linux/debugfs.h>
#include <linux/kfifo.h>
#include <linux/wait.h>
#include <linux/poll.h>
#include <linux/firmware.h>
#include <linux/delay.h>

#include "opengoodix.h"

#define DRIVER_NAME "opengoodixspi"
#define DRIVER_CLASS "opengoodix"
#define SPI_BUF_SIZE 4096

static bool debug_enabled = true;
module_param(debug_enabled, bool, 0644);
MODULE_PARM_DESC(debug_enabled, "Enable debug logging");

/*
 * Protocol Constants (Reverse Engineered)
 * Based on analysis of Windows Driver 1.1.124.12 and live traffic.
 */
#define GOODIX_CMD_RESET    0x0C
#define GOODIX_CMD_WAKE     0xB0
#define GOODIX_CMD_CHIP_ID  0xF0

enum opengoodix_state {
	STATE_UNINITIALIZED,
	STATE_BOOTLOADER,
	STATE_READY,
	STATE_ERROR,
};

/*
 * struct opengoodix_data - Private driver context
 * @spi: Pointer to the SPI device
 * @dev: Pointer to the struct device
 * @cdev: Character device structure
 * @class: Device class for sysfs
 * @devt: Device number (Major/Minor)
 * @lock: Mutex to protect rx_buf access between SPI and read()
 * @tx_buf: DMA-safe buffer for transmission
 * @rx_buf: DMA-safe buffer for reception
 * @last_read_len: Length of valid data in rx_buf
 * @debugfs_dir: Root directory for debugfs
 * @log_fifo: Circular buffer for SPI logs
 * @log_lock: Spinlock for log_fifo
 * @wq: Wait queue for blocking reads
 * @data_ready: Flag indicating data availability
 * @state: Current state of the driver engine
 * @firmware_loaded: Flag indicating if firmware has been loaded
 */
struct opengoodix_data {
	struct spi_device *spi;
	struct device *dev;

	/* Character device support */
	struct cdev cdev;
	struct class *class;
	dev_t devt;

	/* Concurrency control */
	struct mutex lock;

	/* Debugfs & Logging */
	struct dentry *debugfs_dir;
	struct kfifo log_fifo;
	spinlock_t log_lock;

	/* Interrupt Handling */
	wait_queue_head_t wq;
	bool data_ready;

	/* Data buffers (DMA safe) */
	u8 *tx_buf;
	u8 *rx_buf;

	enum opengoodix_state state;
	bool firmware_loaded;
	size_t last_read_len;
};

/* Forward declarations */
static int opengoodix_reset_device(struct opengoodix_data *data);
static int opengoodix_check_chip_state(struct opengoodix_data *data);

/*
 * -------------------------------------------------------------------------
 * Debugfs & Logging
 * -------------------------------------------------------------------------
 */

static void opengoodix_log_packet(struct opengoodix_data *data, const char *tag,
				  u8 *buf, size_t len)
{
	char msg[128];
	int msg_len;

	if (!debug_enabled)
		return;

	/* Log tag and up to 32 bytes of hex data */
	msg_len = snprintf(msg, sizeof(msg), "%s: %*ph\n", tag, (int)min(len, 32UL), buf);

	kfifo_in_spinlocked(&data->log_fifo, msg, msg_len, &data->log_lock);
}

static ssize_t opengoodix_debugfs_read(struct file *file, char __user *user_buf,
				       size_t count, loff_t *ppos)
{
	struct opengoodix_data *data = file->private_data;
	int ret;
	char *bounce_buf;

	if (kfifo_is_empty(&data->log_fifo))
		return 0;

	/* Use a bounce buffer to avoid locking issues with copy_to_user */
	count = min(count, 4096UL);
	bounce_buf = kmalloc(count, GFP_KERNEL);
	if (!bounce_buf)
		return -ENOMEM;

	ret = kfifo_out_spinlocked(&data->log_fifo, bounce_buf, count, &data->log_lock);
	if (ret > 0) {
		if (copy_to_user(user_buf, bounce_buf, ret))
			ret = -EFAULT;
	}

	kfree(bounce_buf);
	return ret;
}

static const struct file_operations opengoodix_debugfs_fops = {
	.owner = THIS_MODULE,
	.open = simple_open,
	.read = opengoodix_debugfs_read,
	.llseek = noop_llseek,
};

/*
 * -------------------------------------------------------------------------
 * SPI Protocol Layer
 * -------------------------------------------------------------------------
 */

/**
 * opengoodix_spi_xfer - Perform a synchronous SPI transfer
 * @data: Driver context
 * @len: Length of data to transmit/receive
 *
 * Wraps spi_sync for this specific device.
 */
static int opengoodix_spi_xfer(struct opengoodix_data *data, size_t len)
{
	struct spi_message m;
	struct spi_transfer t = {
		.tx_buf = data->tx_buf,
		.rx_buf = data->rx_buf,
		.len = len,
		.cs_change = 0,
		.bits_per_word = 8,
	};
	int ret;

	if (len > SPI_BUF_SIZE)
		return -EINVAL;

	spi_message_init(&m);
	spi_message_add_tail(&t, &m);

	opengoodix_log_packet(data, "TX", data->tx_buf, len);

	ret = spi_sync(data->spi, &m);
	if (ret) {
		dev_err(data->dev, "SPI transfer failed: %d\n", ret);
		return ret;
	}

	opengoodix_log_packet(data, "RX", data->rx_buf, len);

	return 0;
}

/*
 * -------------------------------------------------------------------------
 * Character Device Interface
 * -------------------------------------------------------------------------
 */

static int opengoodix_open(struct inode *inode, struct file *file)
{
	struct opengoodix_data *data;

	/* Retrieve our private data from the cdev container */
	data = container_of(inode->i_cdev, struct opengoodix_data, cdev);
	file->private_data = data;

	return nonseekable_open(inode, file);
}

static int opengoodix_release(struct inode *inode, struct file *file)
{
	/* Nothing special to clean up yet */
	return 0;
}

static ssize_t opengoodix_read(struct file *file, char __user *buf,
			       size_t count, loff_t *ppos)
{
	struct opengoodix_data *data = file->private_data;
	ssize_t ret;

	if (data->state != STATE_READY) {
		dev_warn_ratelimited(data->dev,
				     "Read attempted but device not ready (state=%d)\n",
				     data->state);
		return -EBUSY;
	}
	/* TODO: In the future, this might trigger a new capture or read from a ring buffer */

	if (file->f_flags & O_NONBLOCK) {
		if (!data->data_ready)
			return -EAGAIN;
	} else {
		if (wait_event_interruptible(data->wq, data->data_ready))
			return -ERESTARTSYS;
	}

	if (mutex_lock_interruptible(&data->lock))
		return -ERESTARTSYS;

	/* Fetch new data from sensor via SPI */
	if (count > SPI_BUF_SIZE)
		count = SPI_BUF_SIZE;

	/* Send dummy 0x00 bytes to read response */
	memset(data->tx_buf, 0, count);

	if (opengoodix_spi_xfer(data, count) == 0)
		data->last_read_len = count;

	/* Reset file position to treat this as a continuous stream */
	*ppos = 0;

	if (*ppos >= data->last_read_len) {
		mutex_unlock(&data->lock);
		return 0;
	}

	if (copy_to_user(buf, data->rx_buf, count)) {
		ret = -EFAULT;
	} else {
		*ppos += count;
		ret = count;
	}

	data->data_ready = false;
	mutex_unlock(&data->lock);
	return ret;
}

static ssize_t opengoodix_write(struct file *file, const char __user *buf,
				size_t count, loff_t *ppos)
{
	struct opengoodix_data *data = file->private_data;
	int ret;

	if (count > SPI_BUF_SIZE)
		return -EINVAL;

	if (mutex_lock_interruptible(&data->lock))
		return -ERESTARTSYS;

	if (copy_from_user(data->tx_buf, buf, count)) {
		ret = -EFAULT;
		goto out;
	}

	/* Perform the transfer - response will be in rx_buf and logged to debugfs */
	ret = opengoodix_spi_xfer(data, count);
	if (ret == 0) {
		data->last_read_len = count;
		ret = count;
	}

out:
	mutex_unlock(&data->lock);
	return ret;
}

static __poll_t opengoodix_poll(struct file *file, poll_table *wait)
{
	struct opengoodix_data *data = file->private_data;
	__poll_t mask = 0;

	poll_wait(file, &data->wq, wait);

	if (data->data_ready)
		mask |= EPOLLIN | EPOLLRDNORM;

	return mask;
}

static long opengoodix_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
{
	struct opengoodix_data *data = file->private_data;
	int __user *argp = (int __user *)arg;

	switch (cmd) {
	case GOODIX_IOC_GET_STATE:
		if (put_user(data->state, argp))
			return -EFAULT;
		break;
	case GOODIX_IOC_RESET:
		mutex_lock(&data->lock);
		opengoodix_reset_device(data);
		opengoodix_check_chip_state(data);
		mutex_unlock(&data->lock);
		break;
	default:
		return -ENOTTY;
	}
	return 0;
}

static const struct file_operations opengoodix_fops = {
	.owner = THIS_MODULE,
	.open = opengoodix_open,
	.release = opengoodix_release,
	.read = opengoodix_read,
	.write = opengoodix_write,
	.unlocked_ioctl = opengoodix_ioctl,
	.compat_ioctl = opengoodix_ioctl,
	.poll = opengoodix_poll,
};

/*
 * -------------------------------------------------------------------------
 * SPI Driver Lifecycle
 * -------------------------------------------------------------------------
 */

static int opengoodix_reset_device(struct opengoodix_data *data)
{
	int ret;

	dev_info(data->dev, "Resetting device...\n");
	memset(data->tx_buf, GOODIX_CMD_RESET, 4);
	ret = opengoodix_spi_xfer(data, 4);
	if (ret)
		return ret;

	/* Give the chip time to reset */
	msleep(20);
	return 0;
}

static int opengoodix_load_firmware(struct opengoodix_data *data)
{
	const struct firmware *fw;
	size_t offset, chunk_size, payload_len;
	u8 *tx = data->tx_buf;
	int ret;

	dev_info(data->dev, "Requesting firmware: goodix_fp.bin\n");
	ret = request_firmware(&fw, "goodix_fp.bin", data->dev);
	if (ret) {
		dev_warn(data->dev, "Firmware 'goodix_fp.bin' not found (err=%d). Device may not function.\n", ret);
		return ret;
	}

	dev_info(data->dev, "Firmware found, size: %zu bytes. Starting upload...\n", fw->size);

	/*
	 * TODO: Configure Chunk Size
	 * Check analyze_log.py output. Common values: 64, 128, 256.
	 */
	chunk_size = 128;

	for (offset = 0; offset < fw->size; offset += chunk_size) {
		payload_len = min(chunk_size, fw->size - offset);

		/*
		 * TODO: REVERSE ENGINEERED PROTOCOL GOES HERE
		 * Use the 'tx' buffer to construct the packet.
		 *
		 * Example Structure (Uncomment and adjust after analysis):
		 *
		 * tx[0] = 0xF1;                 // Write Command (Guess)
		 * tx[1] = (offset >> 8) & 0xFF; // Address High
		 * tx[2] = offset & 0xFF;        // Address Low
		 * tx[3] = 0x00;                 // Padding?
		 * memcpy(&tx[4], fw->data + offset, payload_len);
		 *
		 * ret = opengoodix_spi_xfer(data, 4 + payload_len);
		 * if (ret) {
		 *     dev_err(data->dev, "Upload failed at %zu\n", offset);
		 *     break;
		 * }
		 */
	}

	/*
	 * TODO: Handshake / Checksum Verification
	 * After uploading, the driver usually sends a command to tell the chip
	 * to verify the checksum and boot the firmware.
	 *
	 * 1. Send Finalize Command (e.g., 0xA0 or specific register write)
	 * 2. Poll Status Register (e.g., read 0x00 repeatedly until 0x01 is returned)
	 */
	
	/* Example Placeholder (based on common Goodix behavior):
	 * dev_info(data->dev, "Verifying firmware checksum...\n");
	 *
	 * // Poll loop
	 * for (int i = 0; i < 50; i++) {
	 *     // Send Status Read Command (e.g., 0x80 00)
	 *     // if (rx[1] == 0x01) break;
	 *     msleep(20);
	 * }
	 *
	 * dev_info(data->dev, "Firmware verified and booted!\n");
	 */
	
	release_firmware(fw);
	return 0;
}

static int opengoodix_check_chip_state(struct opengoodix_data *data)
{
	int ret;

	/* Send CHIP_ID command */
	memset(data->tx_buf, GOODIX_CMD_CHIP_ID, 4);
	ret = opengoodix_spi_xfer(data, 4);
	if (ret)
		return ret;

	/*
	 * Heuristic: If the response is all 0s or all Fs, it's in bootloader mode.
	 * A real response would be something like 00 F0 10 00.
	 */
	if ((data->rx_buf[0] == 0x00 && data->rx_buf[1] == 0x00) ||
	    (data->rx_buf[0] == 0xFF && data->rx_buf[1] == 0xFF)) {
		dev_info(data->dev, "Device appears to be in bootloader mode.\n");
		data->state = STATE_BOOTLOADER;
	} else {
		dev_info(data->dev, "Device appears to be initialized. Chip ID: %*ph\n", 4, data->rx_buf);
		data->state = STATE_READY;
		data->firmware_loaded = true; /* Assume loaded if not in bootloader */
	}
	return 0;
}

/*
 * -------------------------------------------------------------------------
 */

static irqreturn_t opengoodix_irq_handler(int irq, void *dev_id)
{
	struct opengoodix_data *data = dev_id;

	dev_info(data->dev, "ISR: Interrupt received\n");
	data->data_ready = true;
	wake_up_interruptible(&data->wq);
	return IRQ_HANDLED;
}

static int opengoodix_probe(struct spi_device *spi)
{
	struct opengoodix_data *data;
	struct device *dev = &spi->dev;
	int ret;

	dev_info(dev, "Probing Goodix SPI Sensor\n");

	/* Allocate driver context */
	data = devm_kzalloc(dev, sizeof(*data), GFP_KERNEL);
	if (!data)
		return -ENOMEM;

	data->spi = spi;
	data->dev = dev;
	mutex_init(&data->lock);
	data->state = STATE_UNINITIALIZED;

	/* Configure SPI Mode 0 (Standard for Goodix) */
	spi->mode = SPI_MODE_0;
	spi->bits_per_word = 8;
	ret = spi_setup(spi);
	if (ret)
		return ret;

	spi_set_drvdata(spi, data);
	
	/* Init Wait Queue & Fifo (4KB log buffer) */
	init_waitqueue_head(&data->wq);
	if (kfifo_alloc(&data->log_fifo, 4096, GFP_KERNEL))
		return -ENOMEM;
	spin_lock_init(&data->log_lock);

	/* Allocate DMA-safe buffers */
	data->tx_buf = devm_kzalloc(dev, SPI_BUF_SIZE, GFP_KERNEL);
	data->rx_buf = devm_kzalloc(dev, SPI_BUF_SIZE, GFP_KERNEL);
	if (!data->tx_buf || !data->rx_buf)
		return -ENOMEM;

	/* 1. Setup Character Device */
	ret = alloc_chrdev_region(&data->devt, 0, 1, DRIVER_NAME);
	if (ret < 0) {
		kfifo_free(&data->log_fifo);
		dev_err(dev, "Failed to allocate char dev region\n");
		return ret;
	}

	cdev_init(&data->cdev, &opengoodix_fops);
	data->cdev.owner = THIS_MODULE;

	ret = cdev_add(&data->cdev, data->devt, 1);
	if (ret < 0) {
		dev_err(dev, "Failed to add cdev\n");
		goto err_unregister_region;
	}

	/* Handle class_create API change in kernel 6.4 */
#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 4, 0)
	data->class = class_create(DRIVER_CLASS);
#else
	data->class = class_create(THIS_MODULE, DRIVER_CLASS);
#endif
	if (IS_ERR(data->class)) {
		ret = PTR_ERR(data->class);
		dev_err(dev, "Failed to create class\n");
		goto err_del_cdev;
	}

	if (IS_ERR(device_create(data->class, dev, data->devt, NULL, DRIVER_NAME))) {
		ret = PTR_ERR(data->class);
		dev_err(dev, "Failed to create device node\n");
		goto err_destroy_class;
	}

	/* 2. Setup Debugfs */
	data->debugfs_dir = debugfs_create_dir(DRIVER_NAME, NULL);
	debugfs_create_file("spi_log", 0400, data->debugfs_dir, data, &opengoodix_debugfs_fops);

	/* 3. Setup Interrupts */
	if (spi->irq > 0) {
		dev_info(dev, "IRQ %d detected\n", spi->irq);
		ret = devm_request_threaded_irq(dev, spi->irq, NULL,
						opengoodix_irq_handler,
						IRQF_ONESHOT,
						DRIVER_NAME, data);
		if (ret)
			dev_err(dev, "Failed to request IRQ\n");
	}

	/* 4. Initialize Driver Engine and check device state */
	mutex_lock(&data->lock);

	ret = opengoodix_check_chip_state(data);
	if (ret) {
		data->state = STATE_ERROR;
		dev_err(dev, "Failed to check chip state\n");
		/* Don't fail probe, user might be able to fix via write/ioctl */
	}

	if (data->state == STATE_BOOTLOADER)
		opengoodix_load_firmware(data);

	mutex_unlock(&data->lock);

	dev_info(dev, "OpenGoodixSPI initialized. Current state: %d\n", data->state);
	return 0;

err_destroy_class:
	class_destroy(data->class);
err_del_cdev:
	cdev_del(&data->cdev);
err_unregister_region:
	unregister_chrdev_region(data->devt, 1);
	debugfs_remove_recursive(data->debugfs_dir);
	kfifo_free(&data->log_fifo);
	return ret;
}

static void opengoodix_remove(struct spi_device *spi)
{
	struct opengoodix_data *data = spi_get_drvdata(spi);

	dev_info(&spi->dev, "Removing OpenGoodixSPI driver\n");

	debugfs_remove_recursive(data->debugfs_dir);
	kfifo_free(&data->log_fifo);
	device_destroy(data->class, data->devt);
	class_destroy(data->class);
	cdev_del(&data->cdev);
	unregister_chrdev_region(data->devt, 1);
}

/*
 * ACPI Match Table
 * Note: "GXFP5187" is a common ID for Goodix sensors on Huawei laptops.
 * Check your cat /sys/bus/acpi/devices/.../modalias to confirm yours.
 */
static const struct acpi_device_id opengoodix_acpi_match[] = {
	{ "GXFP5187", 0 },
	{ "GXFP3287", 0 },
	{ "GXFP51A0", 0 },
	{ "GXFP0000", 0 }, /* Generic placeholder */
	{ },
};
MODULE_DEVICE_TABLE(acpi, opengoodix_acpi_match);

static const struct spi_device_id opengoodix_spi_id[] = {
	{ "opengoodix", 0 },
	{ }
};
MODULE_DEVICE_TABLE(spi, opengoodix_spi_id);

static struct spi_driver opengoodix_driver = {
	.driver = {
		.name = DRIVER_NAME,
		.acpi_match_table = opengoodix_acpi_match,
	},
	.probe = opengoodix_probe,
	.remove = opengoodix_remove,
	.id_table = opengoodix_spi_id,
};

module_spi_driver(opengoodix_driver);

MODULE_AUTHOR("OpenGoodixSPI Contributors");
MODULE_DESCRIPTION("Experimental Goodix SPI Fingerprint Driver");
MODULE_LICENSE("GPL");
MODULE_VERSION("0.1.0");