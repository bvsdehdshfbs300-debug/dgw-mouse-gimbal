#include <ctype.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "driver/gpio.h"
#include "esp_rom_sys.h"
#include "esp_vfs_dev.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#define X_STEP_PIN GPIO_NUM_7
#define X_DIR_PIN  GPIO_NUM_15
#define X_EN_PIN   GPIO_NUM_16

#define Y_STEP_PIN GPIO_NUM_4
#define Y_DIR_PIN  GPIO_NUM_5
#define Y_EN_PIN   GPIO_NUM_6

#define LASER_PIN GPIO_NUM_6
#define LASER_ACTIVE_LEVEL 1

#define USE_ENABLE_PINS 0
#define ENABLE_ACTIVE_LEVEL 1

#define X_DIR_POSITIVE_LEVEL 1
#define Y_DIR_POSITIVE_LEVEL 1

#define MIN_STEP_HALF_PERIOD_US 80
#define YIELD_EVERY_PULSES 256

static unsigned int step_half_period_us = 500;
static bool laser_enabled = false;

static void write_laser(bool enabled)
{
    laser_enabled = enabled;
    gpio_set_level(LASER_PIN, enabled ? LASER_ACTIVE_LEVEL : !LASER_ACTIVE_LEVEL);
}

static void write_enable(bool enabled)
{
    if (!USE_ENABLE_PINS) {
        return;
    }

    int level = enabled ? ENABLE_ACTIVE_LEVEL : !ENABLE_ACTIVE_LEVEL;
    gpio_set_level(X_EN_PIN, level);
    gpio_set_level(Y_EN_PIN, level);
}

static void set_direction(gpio_num_t dir_pin, bool positive, bool positive_level)
{
    gpio_set_level(dir_pin, positive == positive_level);
    esp_rom_delay_us(5);
}

static void pulse_pin(gpio_num_t step_pin)
{
    gpio_set_level(step_pin, 1);
    esp_rom_delay_us(step_half_period_us);
    gpio_set_level(step_pin, 0);
    esp_rom_delay_us(step_half_period_us);
}

static void slow_test_axis(gpio_num_t step_pin, gpio_num_t dir_pin, bool positive_level, long steps)
{
    if (steps == 0) {
        return;
    }

    set_direction(dir_pin, steps > 0, positive_level);
    unsigned long count = labs(steps);

    for (unsigned long i = 0; i < count; ++i) {
        gpio_set_level(step_pin, 1);
        vTaskDelay(pdMS_TO_TICKS(20));
        gpio_set_level(step_pin, 0);
        vTaskDelay(pdMS_TO_TICKS(20));
    }
}

static void move_axis(gpio_num_t step_pin, gpio_num_t dir_pin, bool positive_level, long steps)
{
    if (steps == 0) {
        return;
    }

    set_direction(dir_pin, steps > 0, positive_level);
    unsigned long count = labs(steps);

    for (unsigned long i = 0; i < count; ++i) {
        pulse_pin(step_pin);
        if ((i + 1) % YIELD_EVERY_PULSES == 0) {
            vTaskDelay(1);
        }
    }
}

static void move_both(long x_steps, long y_steps)
{
    if (x_steps == 0 && y_steps == 0) {
        return;
    }

    set_direction(X_DIR_PIN, x_steps >= 0, X_DIR_POSITIVE_LEVEL);
    set_direction(Y_DIR_PIN, y_steps >= 0, Y_DIR_POSITIVE_LEVEL);

    unsigned long ax = labs(x_steps);
    unsigned long ay = labs(y_steps);
    unsigned long major = ax > ay ? ax : ay;

    unsigned long err_x = 0;
    unsigned long err_y = 0;

    for (unsigned long i = 0; i < major; ++i) {
        bool pulse_x = false;
        bool pulse_y = false;

        err_x += ax;
        if (err_x >= major) {
            err_x -= major;
            pulse_x = ax > 0;
        }

        err_y += ay;
        if (err_y >= major) {
            err_y -= major;
            pulse_y = ay > 0;
        }

        if (pulse_x) {
            gpio_set_level(X_STEP_PIN, 1);
        }
        if (pulse_y) {
            gpio_set_level(Y_STEP_PIN, 1);
        }

        esp_rom_delay_us(step_half_period_us);

        if (pulse_x) {
            gpio_set_level(X_STEP_PIN, 0);
        }
        if (pulse_y) {
            gpio_set_level(Y_STEP_PIN, 0);
        }

        esp_rom_delay_us(step_half_period_us);

        if ((i + 1) % YIELD_EVERY_PULSES == 0) {
            vTaskDelay(1);
        }
    }
}

static void print_help(void)
{
    puts("OK mouse_gimbal");
    puts("Commands: X n | Y n | M x y | T X/Y n | P us | E 0/1 | L 0/1/T | ?");
}

static void handle_command(char *cmd)
{
    while (isspace((unsigned char)*cmd)) {
        ++cmd;
    }

    size_t len = strlen(cmd);
    while (len > 0 && isspace((unsigned char)cmd[len - 1])) {
        cmd[--len] = '\0';
    }

    if (len == 0) {
        return;
    }

    char op = (char)toupper((unsigned char)cmd[0]);

    if (op == '?') {
        print_help();
        return;
    }

    if (op == 'X') {
        long steps = strtol(cmd + 1, NULL, 10);
        move_axis(X_STEP_PIN, X_DIR_PIN, X_DIR_POSITIVE_LEVEL, steps);
        puts("OK");
    } else if (op == 'Y') {
        long steps = strtol(cmd + 1, NULL, 10);
        move_axis(Y_STEP_PIN, Y_DIR_PIN, Y_DIR_POSITIVE_LEVEL, steps);
        puts("OK");
    } else if (op == 'M') {
        char *p = cmd + 1;
        long x_steps = strtol(p, &p, 10);
        long y_steps = strtol(p, &p, 10);
        move_both(x_steps, y_steps);
        puts("OK");
    } else if (op == 'T') {
        char *p = cmd + 1;
        while (isspace((unsigned char)*p)) {
            ++p;
        }
        char axis = (char)toupper((unsigned char)*p++);
        long steps = strtol(p, NULL, 10);
        if (axis == 'X') {
            slow_test_axis(X_STEP_PIN, X_DIR_PIN, X_DIR_POSITIVE_LEVEL, steps);
            puts("OK");
        } else if (axis == 'Y') {
            slow_test_axis(Y_STEP_PIN, Y_DIR_PIN, Y_DIR_POSITIVE_LEVEL, steps);
            puts("OK");
        } else {
            puts("ERR T needs X or Y");
        }
    } else if (op == 'P') {
        long period = strtol(cmd + 1, NULL, 10);
        if (period < MIN_STEP_HALF_PERIOD_US) {
            period = MIN_STEP_HALF_PERIOD_US;
        }
        step_half_period_us = (unsigned int)period;
        printf("OK P %u\n", step_half_period_us);
    } else if (op == 'E') {
        long enabled = strtol(cmd + 1, NULL, 10);
        write_enable(enabled != 0);
        puts("OK");
    } else if (op == 'L') {
        char *p = cmd + 1;
        while (isspace((unsigned char)*p)) {
            ++p;
        }
        char value = (char)toupper((unsigned char)*p);
        if (value == 'T') {
            write_laser(!laser_enabled);
        } else {
            write_laser(strtol(p, NULL, 10) != 0);
        }
        printf("OK L %d\n", laser_enabled ? 1 : 0);
    } else {
        puts("ERR unknown command");
    }
}

static void configure_gpio(void)
{
    gpio_config_t output_conf = {
        .pin_bit_mask = (1ULL << X_STEP_PIN) |
                        (1ULL << X_DIR_PIN) |
                        (1ULL << X_EN_PIN) |
                        (1ULL << Y_STEP_PIN) |
                        (1ULL << Y_DIR_PIN) |
                        (1ULL << LASER_PIN),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };

    gpio_config(&output_conf);
    gpio_set_level(X_STEP_PIN, 0);
    gpio_set_level(Y_STEP_PIN, 0);
    write_laser(false);
    write_enable(true);
}

void app_main(void)
{
    configure_gpio();
    setvbuf(stdin, NULL, _IONBF, 0);
    setvbuf(stdout, NULL, _IONBF, 0);

    print_help();

    char line[96];
    size_t pos = 0;

    while (true) {
        int c = getchar();
        if (c == EOF) {
            vTaskDelay(pdMS_TO_TICKS(10));
            continue;
        }

        if (c == '\n' || c == '\r') {
            line[pos] = '\0';
            handle_command(line);
            pos = 0;
        } else if (pos < sizeof(line) - 1) {
            line[pos++] = (char)c;
        }
    }
}
