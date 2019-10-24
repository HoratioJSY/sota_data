import collections
import pickle
import json
import re
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from urllib import request
from tqdm import tqdm


def abs_reader():
    df_a = pd.read_csv('./data/Sota_Evaluations.csv')
    df_a = df_a.dropna(axis=0)
    url = df_a['paperurl']
    total_abs = {}
    try:
        with open('./data/saved_abs_test.p', 'rb') as f:
            total_abs = pickle.load(f)
    except:
        i = 1
        for u in tqdm(url[:100]):
            if u.find('arxiv') > -1:
                try:
                    r = request.urlopen(u).read()
                    content = BeautifulSoup(r, features='html.parser')
                    abs_ = content.find('blockquote', attrs={'abstract'}).get_text().strip()[11:]
                    total_abs[u] = re.sub(r'\n', ' ', abs_)
                except:
                    print(i)
                    i += 1
                    continue
        with open('./data/saved_abs_test.p', 'wb') as f:
            pickle.dump(total_abs, f)
            print('abs saved, total num are %d' % len(total_abs))
    return total_abs


def abs_filter():
    total_abs = abs_reader()
    print('total abs: ', len(total_abs))

    df_m = pd.read_excel('./data/Metric.xlsx')
    df_m = df_m.dropna(axis=0)

    metric_name = np.array(df_m['dbtech'])
    token_list = ' '.join(metric_name).lower().translate(str.maketrans("（）()", "    ")).split()
    key_words, _ = zip(*collections.Counter(token_list).most_common(20))

    filter_pattern = re.compile(r'\s(%s)\s' % ('|'.join(key_words)), re.I)
    filted_abs = [(url_, abs_) for url_, abs_ in total_abs.items() if filter_pattern.search(abs_) is not None]
    print('filted: ', len(filted_abs))
    return filted_abs, metric_name


def levenshtein_distance(string_one, string_two):
    if len(string_one) < len(string_two): return levenshtein_distance(string_two, string_one)
    # TO DO: a method to normalizing score that take no effects of ranking
    if len(string_two) == 0: return len(string_one)

    previous_row = range(len(string_two) + 1)
    for index_1, chr_1 in enumerate(string_one):
        # current_raw[o] equals to chr num in string two
        current_row = [index_1 + 1]

        for index_2, chr_2 in enumerate(string_two):
            insertions = previous_row[index_2 + 1] + 1
            deletions = current_row[index_2] + 1

            # 1 for true, 0 for false
            substitutions = previous_row[index_2] + (chr_1 != chr_2)
            current_row.append(min(insertions, deletions, substitutions))

        # after loop, the length of current_raw must equals to len(s2)+1
        previous_row = current_row
    return previous_row[-1]


def abs_extraction():
    filted_abs, metric_name = abs_filter()
    num_pattern = re.compile(r'\d+%|\d+\.\d+%|\d+\.\d+')
    # ' '.join(metric_name).split()
    key_pattern = re.compile("\s(%s)(\s|\,|\.)" % ('|'.join(metric_name)), re.I)
    valued_abs = [abs_ for abs_ in filted_abs if num_pattern.search(abs_[-1]) is not None]

    extraction_results = {}
    for url, abs_ in valued_abs:
        result = {}
        lines = re.split(r'\.\s', abs_)

        informative_line = [line for line in lines
                            if num_pattern.search(line) is not None
                            and key_pattern.search(line) is not None]

        if len(informative_line) > 0:
            result['informative_line: '] = informative_line

            key_list = [i.group()[1:-1] for i in key_pattern.finditer(informative_line[0])]
            num_list = [i.group() for i in num_pattern.finditer(informative_line[0])]
            # print(key_list)
            # print(num_list)

            if len(key_list) > len(num_list): key_list = key_list[: len(num_list)]
            if len(key_list) > 0:
                result['results: '] = [key_list, num_list]

            extraction_results[url] = result
    return extraction_results


results = abs_extraction()
with open('./data/abs_sample.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=4)

