// Copyright 2015-2016 Espressif Systems (Shanghai) PTE LTD
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at

//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

/* Notes:
 * 1. Put all task priority and stack size definition in this file
 * 2. If the task priority is less than 10, use ESP_TASK_PRIO_MIN + X style,
 *    otherwise use ESP_TASK_PRIO_MAX - X style
 * 3. If this is a daemon task, the macro prefix is ESP_TASKD_, otherwise
 *    it's ESP_TASK_
 * 4. If the configMAX_PRIORITIES is modified, please make all priority are
 *    greater than 0
 * 5. Make sure esp_task.h is consistent between wifi lib and idf
 */

#ifndef _ESP_TASK_H_
#define _ESP_TASK_H_

#include "sdkconfig.h"
#include "freertos/FreeRTOSConfig.h"
#include "task_runner_defs.h"

#define ESP_TASK_PRIO_MAX (configMAX_PRIORITIES)
#define ESP_TASK_PRIO_MIN (0)

/* Bt contoller Task */
/* controller */
#define ESP_TASK_BT_CONTROLLER_PRIO   (ESP_TASK_PRIO_MAX - 2)
#ifdef CONFIG_NEWLIB_NANO_FORMAT
#define TASK_EXTRA_STACK_SIZE      (0)
#else
#define TASK_EXTRA_STACK_SIZE      (512)
#endif

#define BT_TASK_EXTRA_STACK_SIZE      TASK_EXTRA_STACK_SIZE
#define ESP_TASK_BT_CONTROLLER_STACK  (3584 + TASK_EXTRA_STACK_SIZE)


/* idf task */
#define ESP_TASK_TIMER_PRIO           (TASK_ESP_TIMER_PRIORITY)
#define ESP_TASK_TIMER_STACK          (CONFIG_ESP_TIMER_TASK_STACK_SIZE +  TASK_EXTRA_STACK_SIZE)
#define ESP_TASKD_EVENT_PRIO          (TASK_ESP_EVENT_PRIORITY)
#define ESP_TASKD_EVENT_STACK         (CONFIG_ESP_SYSTEM_EVENT_TASK_STACK_SIZE + TASK_EXTRA_STACK_SIZE)
#define ESP_TASK_TCPIP_PRIO           (TASK_TCPIP_PRIORITY)
#define ESP_TASK_TCPIP_STACK          (CONFIG_LWIP_TCPIP_TASK_STACK_SIZE + TASK_EXTRA_STACK_SIZE)
#define ESP_TASK_MAIN_PRIO            (ESP_TASK_PRIO_MIN + 1)
#define ESP_TASK_MAIN_STACK           (CONFIG_ESP_MAIN_TASK_STACK_SIZE + TASK_EXTRA_STACK_SIZE)

#endif
