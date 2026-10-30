#include <stdio.h>
#include <unistd.h>
#include "lidar.h"

static void on_frame(struct lidar_dev *dev,
                     const struct lidar_frame *frame, void *ctx)
{
    (void)dev;
    (void)ctx;
    printf("points=%u\n", frame->point_count);
}

int main(void)
{
    struct lidar_dev *dev = lidar_alloc_uart(
        "my_lidar", "/dev/ttyUSB0", 115200, "YDLIDAR", NULL);
    struct lidar_config cfg = {
        .rpm = 600,
        .angle_min_deg = -180.0f,
        .angle_max_deg = 180.0f,
        .range_min_m = 0.1f,
        .range_max_m = 12.0f,
        .return_mode = 0,
        .enable_transform = false,
    };

    if (!dev) {
        fprintf(stderr, "Failed to create LIDAR device\n");
        return 1;
    }

    if (lidar_init(dev, &cfg) < 0) {
        fprintf(stderr, "Failed to initialize LIDAR\n");
        lidar_free(dev);
        return 1;
    }

    lidar_set_callback(dev, on_frame, NULL);
    if (lidar_start(dev) < 0) {
        fprintf(stderr, "Failed to start LIDAR\n");
        lidar_stop(dev);
        lidar_free(dev);
        return 1;
    }

    sleep(3);

    int ret = lidar_stop(dev);
    lidar_free(dev);
    return ret < 0 ? 1 : 0;
}
