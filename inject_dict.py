import json, re

dict_data = {}
with open('/Users/subarupan/Developer/wugniu_zaonhe_dic.yaml', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'): continue
        parts = line.split('\t')
        if len(parts) >= 2:
            word = parts[0].strip()
            pronunciation = parts[1].strip()
            
            weight = 100
            if len(parts) >= 3:
                weight_str = parts[2].strip()
                if weight_str:
                    weight_str_clean = weight_str.replace('%', '')
                    try:
                        weight = float(weight_str_clean)
                    except ValueError:
                        weight = 100
            
            if word not in dict_data: dict_data[word] = []
            existing = [p['pronunciation'] for p in dict_data[word]]
            if pronunciation not in existing:
                dict_data[word].append({'pronunciation': pronunciation, 'weight': weight})

from opencc import OpenCC
cc = OpenCC('t2s')
final_dict = {}
for word in dict_data:
    dict_data[word].sort(key=lambda x: x['weight'], reverse=True)
    prons = [x['pronunciation'] for x in dict_data[word]]
    max_weight = dict_data[word][0]['weight'] if dict_data[word] else 100
    simp = cc.convert(word)
    final_dict[word] = {
        "s": simp,
        "p": prons,
        "w": max_weight
    }

js_dict = json.dumps(final_dict, ensure_ascii=False)
js_dict = json.dumps(final_dict, ensure_ascii=False)
js_content = f"const WUGNIU_DICT = {js_dict};\n"

with open('dict.js', 'w', encoding='utf-8') as f:
    f.write(js_content)

print("Dictionary extracted to dict.js successfully")
