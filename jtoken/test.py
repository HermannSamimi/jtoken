import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import jtoken
raw = open("/Users/hermann/Documents/jtoken-2/jtoken/data.json").read()
data = raw

encoded = jtoken.encode(data)
print(encoded)

# decoded = jtoken.decode(encoded)
# print(decoded)
