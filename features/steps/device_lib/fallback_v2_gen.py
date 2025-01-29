import argparse
import json
import random
import string

if __name__ == '__main__':
    """Generates Fallback V2 result JSON"""

    parser = argparse.ArgumentParser()
    parser.add_argument('-cnr', '--nr_of_cards', required=True, help='100')
    parser.add_argument('-snr', '--nr_of_schdules_per_card', required=False,
                        help='Give this parameter if you want an exact number per cards, otherwise it is random [1;15]')
    parser.add_argument('-rnr', '--nr_of_relays_per_schedule', required=False,
                        help='Give this parameter if you want an exact number per schedule, otherwise it is random [1;65]')
    parser.add_argument('-c', '--c_string_format', required=False,
                        help='Add this parameter to make the output C like string')
    args = parser.parse_args()

    max_nr_of_relays = 65
    max_nr_of_schedules = 15

    data = {}
    data['session_id'] = 'session-820923084792'
    result_object = {}
    result_array_item = {}
    relay_array = []

    j = 0
    i = 0

    while i < int(args.nr_of_cards):
        card_id = str(''.join(random.choices(
            string.ascii_lowercase + string.digits, k=15)))
        if (args.nr_of_schdules_per_card):
            number_of_schedules = int(args.nr_of_schdules_per_card)
        else:
            number_of_schedules = random.randint(1, max_nr_of_schedules)
        schedule_array = []
        k = 0

        schedule_ids = random.sample(
            range(0, max_nr_of_schedules), number_of_schedules)

        while k < number_of_schedules:
            relay_array = []
            schedule_array_item = {}
            if (args.nr_of_relays_per_schedule):
                relay_array_size = int(args.nr_of_relays_per_schedule)
            else:
                relay_array_size = random.randint(1, max_nr_of_relays)
            result_array_item = {}

            relay_array = random.sample(
                range(0, max_nr_of_relays), relay_array_size)
            relay_array.sort()

            schedule_array_item['r'] = relay_array
            schedule_array_item['s'] = schedule_ids[k]

            schedule_array.append(schedule_array_item)
            k = k + 1

        result_object[card_id] = schedule_array
        i = i + 1

    data['result'] = result_object

    with open('fallback_res.json', 'w') as f:
        if args.c_string_format:
            json.dump(json.dumps(data), f)
        else:
            json.dump(data, f)
