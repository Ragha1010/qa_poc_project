import argparse
import json
from unittest import result
import random
import secrets

if __name__ == '__main__':
    """Generates Fallback V1 result JSON"""

    parser = argparse.ArgumentParser()
    parser.add_argument('-cnr', '--nr_of_cards', required=True, help='100')
    args = parser.parse_args()

    max_relay_number = 64

    data = {}
    data['session_id'] = 'session-820923084792'
    result_array = []
    result_array_item = {}
    relay_array = []
    relay_array_size = random.randint(1, max_relay_number)

    j = 0
    i = 0

    while i < int(args.nr_of_cards):
        j = 0
        relay_array = []
        relay_array_size = random.randint(1, max_relay_number)
        result_array_item = {}

        while j < relay_array_size:
            relay_array.append( random.randint(0, max_relay_number) )
            j = j + 1
        relay_array.sort()

        result_array_item['c'] = secrets.token_hex(16)
        result_array_item['r'] = relay_array
        result_array_item['s'] = random.randint(0, 15)

        result_array.append(result_array_item)
        i = i + 1

    data['result'] = result_array

    # convert into JSON:
    y = json.dumps(data)

    # the result is a JSON string:
    with open('fallback_res.json', 'w') as f:
        json.dump(data, f)