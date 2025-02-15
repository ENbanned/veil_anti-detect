import json

with open('results.jsonl', 'r', encoding='utf-8') as file:
    data = [json.loads(line) for line in file]
    
lst = set()
 
for i in data:
    lst.add(str(i))
    
print(len(lst))