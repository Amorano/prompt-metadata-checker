"""Translate old model hash db into new modeldb."""

import os
import re
import json
import urllib.request as req

api_url_civitai = f"https://civitai.com/api/v1/models?type=Checkpoint&limit=100&nsfw=false&page="

filters = [
    ('type', 'Checkpoint'),
    ('stats.rating', 4.9),
    ('stats.downloadCount', 500),
    ('stats.favoriteCount', 1)
]

def pluckends(v):
    size = 0
    while size != len(v):
        size = len(v)
        v = v.strip()
        v = v.strip('_')
        v = v.strip('v')
    return v

# scrape all the model information we can -- it is open to use
def civitai_modelScrape():
    opener = req.URLopener()
    opener.addheader('User-Agent', 'ai-looking-for-friends')
    idx = 0
    while (idx := idx + 1):
        url = f"{api_url_civitai}{idx}"
        filenext = f"data/data_{idx}.json"
        try:
            _, _ = opener.retrieve(url, filenext)
        except Exception as e:
            print(e)
            break

        data = {}
        with open(filenext, "r", encoding="utf-8") as f:
            data = json.load(f)
            if (items := data.get('items', None)) is None or len(items) == 0:
                break

# use the files from the civitai scrape to form master modelhash db
def crunchJsonFiles():
    # for version checking... maybe flex out into a regex boi

    counter = 0
    parsed = {}

    # the map of hashes to single version entries.
    modelMap = {}

    for parse in os.listdir('data'):
        if not parse.startswith('data_'):
            continue

        try:
            with open(f"data/{parse}", "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(e)
            continue

        for model in data['items']:
            if (versions := model.get('modelVersions', None)) is None:
                continue

            # filter...
            passed = False
            for f, value in filters:
                parts = f.split('.')
                d = dict(model)
                for p in parts:
                    if (d := d.get(p, None)) is None:
                        print("no param: {p} in {model['name']}")
                        break

                if d:
                    if isinstance(d, (bool, str)):
                        passed = d == value
                    elif isinstance(d, (int, float)):
                        passed = d >= value
                    else:
                        print('unknown type {d}')

                if not passed:
                    break

            if not passed:
                continue

            modelname = model['name'].replace(' - Fantasy.ai', '')
            modelname = modelname.replace('[Stylized Anime Model]', '')
            modelname = modelname.replace('[pruned fp16 ckpt]', '')
            modelname = modelname.replace('[pruned fp16]', '')
            modelname = modelname.replace('[pruned fp32]', '')
            modelname = modelname.replace(' fp16', '')
            modelname = modelname.replace('V1.3', '')
            modelname = modelname.replace('Counterfeit-V2.5', 'Counterfeit')
            modelname = modelname.replace('Official Release', '')
            modelname = modelname.replace('-fp16', '')
            modelname = modelname.replace('_', ' ')
            modelname = modelname.replace('\u56fd', '')
            modelname = modelname.replace('\u98ce', '')
            modelname = modelname.strip().title()

            for v in versions:
                version = [v['name'], 'v1'][model['name'] == v['name']]
                version = version.lower()
                version = pluckends(version)
                version = version.replace('fantasy.ai', '')
                version = version.replace('meina', '')
                version = version.replace('cetusmix_', '')
                version = re.sub(r"cetus.version(\d)", r"v\1", version, flags=re.I)
                lower = model['name'].lower()
                version = version.replace(lower, '')
                lower = lower.split(' ')[0]
                version = version.replace(lower, '')
                version = version.replace(modelname.lower(), '')
                version = version.replace('[', '')
                version = version.replace(']', '')
                version = version.replace('ckpt', '')
                version = pluckends(version)
                version = version.replace('ersion ', 'v')

                # just try to pretty the version number to be consistently float
                try:
                    version = float(version) / 1.
                except Exception as _:
                    pass
                    # print(version)

                version = str(version)
                full = f"{modelname} {version}"
                for fileinfo in v['files']:
                    for h in fileinfo['hashes'].values():
                        if modelMap.get(full, None) is None:

                            modelMap[full] = {
                                'm': modelname,
                                'v': version
                            }

                        # keep the hashes all lower for 1:1 compares
                        parsed[h.lower()] = full

            counter += 1

    print(counter)

    with open('data/hashCore.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    for k, v in data.items():
        k = k.lower().title()
        if parsed.get(k, None) is None:
            m = v['m'].strip().title()
            v = v['v'].strip().strip('v')
            full = f"{m} {v}"
            if modelMap.get(full, None) is None:
                modelMap[full] = {
                    'm': m,
                    'v': v
                }
                parsed[k] = full

    with open('src/vendor/postie/modelHash.js', 'w', encoding='utf-8') as f:
        f.write("const modelHash = ")
        json.dump(parsed, f, indent=2)
        f.write("\n\n")
        f.write("export default modelHash;\n")

    with open('src/vendor/postie/modelMap.js', 'w', encoding='utf-8') as f:
        f.write("const modelMap = ")
        json.dump(modelMap, f, indent=2, sort_keys=True)
        f.write("\n\n")
        f.write("export default modelMap;\n")

# builds the main data store from civitai
# civitai_modelScrape()

# processes civitai files and adds models already established on PH
crunchJsonFiles()
