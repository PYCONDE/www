from pprint import pprint
import json

with open('/Users/hendorf/Documents/code/PyConDE-www/_private/submissions.json') as f:
    data = json.load(f)

opt_out = [(x['title'], x['state']) for x in data if x['do_not_record']]

print(opt_out)