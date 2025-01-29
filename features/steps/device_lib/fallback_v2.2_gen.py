import argparse
import json
import random
import string


if __name__ == '__main__':
    """Generates Fallback V2.2 result JSON"""

    parser = argparse.ArgumentParser()
    parser.add_argument('-cnr', '--nr_of_cards', required=True, help='100')
    parser.add_argument('-cid', '--card_id_length', required=False,
                        help='Give this parameter if you want an exact card id length, otherwise it is random [8;15]')
    parser.add_argument('-snr', '--nr_of_schdules_per_card', required=False,
                        help='Give this parameter if you want an exact number per cards, otherwise it is random [1;16] 15 + \"0\"')
    parser.add_argument('-rnr', '--nr_of_relays_per_schedule', required=False,
                        help='Give this parameter if you want an exact number per schedule, otherwise it is random [1;65] 64 + \"0\"')
    parser.add_argument('-c', '--c_string_format', required=False,
                        help='Add this parameter to make the output C like string')
    args = parser.parse_args()

    max_nr_of_relays = 65
    max_nr_of_schedules = 16
    desfire_id_length = 8
    apple_id_length = 11
    max_id_length = 15

    data = {}
    data['session_id'] = 'session-820923084792'
    result_object = {}
    result_array_item = {}
    relay_array = []

    j = 0
    i = 0

    while i < int(args.nr_of_cards):
        if (args.card_id_length):
            card_id = str(''.join(random.choices(
                string.ascii_lowercase + string.digits, k=int(args.card_id_length))))
        else:
            card_id = str(''.join(random.choices(
                string.ascii_lowercase + string.digits, k=random.randint(desfire_id_length, max_id_length))))

        if (args.nr_of_schdules_per_card):
            number_of_schedules = int(args.nr_of_schdules_per_card)
        else:
            number_of_schedules = random.randint(1, max_nr_of_schedules)
        schedule_array = []
        k = 0

        schedule_ids = random.sample(
            range(0, max_nr_of_schedules), number_of_schedules)
        schedule_ids.sort()
        card = {}

        while k < number_of_schedules:
            relay_array = []
            relay_array_hex = [0, 0, 0, 0, 0, 0, 0, 0, 0]
            if (args.nr_of_relays_per_schedule):
                relay_array_size = int(args.nr_of_relays_per_schedule)
            else:
                relay_array_size = random.randint(1, max_nr_of_relays)
            result_array_item = {}

            relay_array = random.sample(
                range(0, max_nr_of_relays), relay_array_size)
            relay_array.sort()

            if relay_array[0] == 0:
                relay_array_hex[0] = 1
            else:
                relay_array_hex[0] = 0

            relay_array_hex2 = 0
            for relay_nr in relay_array[1:]:
                relay_array_hex2 = relay_array_hex2 | (1 << (relay_nr - 1))

            schedule = str(relay_array_hex[0]) + "|" + hex(relay_array_hex2)

            card[schedule_ids[k]] = schedule
            k = k + 1

        result_object[card_id] = card
        i = i + 1

    data['result'] = result_object

    with open('fallback_res.json', 'a') as f:
        if args.c_string_format:
            json.dump(json.dumps(data), f)
        else:
            json.dump(data, f)
        f.write("\n")
