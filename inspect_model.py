import app
from collections import Counter
names = [l.name for l in app.MODEL.layers]
print('Total layers:', len(names))
from collections import Counter
ctr = Counter(names)
dups = [n for n,c in ctr.items() if c>1]
print('Duplicate layer names:', dups)
for i,l in enumerate(app.MODEL.layers[:200]):
    try:
        print(i, l.name, l.output_shape)
    except Exception:
        print(i, l.name)
