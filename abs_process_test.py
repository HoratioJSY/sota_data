import re
import json
import pickle
import numpy as np
import pandas as pd
from tqdm import tqdm
from urllib import request
from bs4 import BeautifulSoup
from fuzzywuzzy import process


def abs_reader(code_url=True):
    df_a = pd.read_csv('./data/Sota_Evaluations.csv')
    df_a = df_a.dropna(axis=0)
    url = df_a['paperurl'][:200]
    total_abs = {}
    total_code = {}
    try:
        with open('./data/saved_abs_test.p', 'rb') as f:
            total_abs = pickle.load(f)
    except:
        i = 1
        # url = ['https://arxiv.org/abs/1912.02424v1', "https://arxiv.org/abs/1912.01954v2",
        #        "https://arxiv.org/abs/1912.01865v1", "https://arxiv.org/abs/1811.11742v2"]
        for u in tqdm(url):
            if u.find('arxiv') > -1:
                try:
                    r = request.urlopen(u).read()
                    content = BeautifulSoup(r, features='html.parser')
                    abs_content = content.find('blockquote', attrs={'abstract'})
                    abs_ = abs_content.get_text().strip()[11:]
                    total_abs[u] = re.sub(r'\n', ' ', abs_)

                    if code_url:
                        code_ = abs_content.find(class_='link-external')
                        if code_ is not None:
                            code_ = code_['href'].strip()
                            total_code[u] = code_

                except:
                    print(i)
                    i += 1
                    continue
        with open('./data/saved_abs_test.p', 'wb') as f:
            pickle.dump(total_abs, f)
            print('abs saved, total num are %d' % len(total_abs))
    return total_abs, total_code


def abs_filter(evidence=False):
    total_abs, _ = abs_reader()
    print('total abs: ', len(total_abs))

    with open("./data/metric_tag.json", 'r') as f:
        metric_name = json.load(f)

    filter_pattern = re.compile(r'\s(%s)\s' % ('|'.join(metric_name)), re.I)

    filtered_abs = []
    filtered_lines = []

    # whether we should output evidence lines that filtering abstract
    if evidence:
        for url_, abs_ in total_abs.items()[:100]:
            lines = re.split(r'\.\s', abs_)
            evidence_line = [line for line in lines if filter_pattern.search(line) is not None]
            if len(evidence_line) > 0:
                filtered_abs.append((url_, abs_))
                filtered_lines.append(evidence_line)
        assert len(filtered_abs) == len(filtered_lines)

        return filtered_abs, filtered_lines, metric_name
    else:
        filtered_abs = [(url_, abs_) for url_, abs_ in total_abs.items() if filter_pattern.search(abs_) is not None]
        return filtered_abs, metric_name


# def levenshtein_distance(string_one, string_two):
#     if len(string_one) < len(string_two): return levenshtein_distance(string_two, string_one)
#     # TO DO: a method to normalizing score that take no effects of ranking
#     if len(string_two) == 0: return len(string_one)
#
#     previous_row = range(len(string_two) + 1)
#     for index_1, chr_1 in enumerate(string_one):
#         # current_raw[o] equals to chr num in string two
#         current_row = [index_1 + 1]
#
#         for index_2, chr_2 in enumerate(string_two):
#             insertions = previous_row[index_2 + 1] + 1
#             deletions = current_row[index_2] + 1
#
#             # 1 for true, 0 for false
#             substitutions = previous_row[index_2] + (chr_1 != chr_2)
#             current_row.append(min(insertions, deletions, substitutions))
#
#         # after loop, the length of current_raw must equals to len(s2)+1
#         previous_row = current_row
#     return previous_row[-1]


def string_distance(string, key_list, value_list):
    key_position = sorted(list(set([np.mean(i.span()) for key in key_list
                                    for i in re.finditer(key, string)])))
    value_position = sorted(list(set([np.mean(i.span()) for value in value_list
                                      for i in re.finditer(value, string)])))
    # assert len(key_position) == len(key_list)
    # assert len(value_position) == len(value_list)
    # print(key_position)
    # print(value_position)
    if len(key_list) >= len(value_list):
        index = [np.argmin(np.abs([i - j for j in key_position])) for i in value_position]
        # assert len(index) == len(value_list)
        # matched = zip([key_list[i] for i in index], value_list)
        # same key indexed by different value
        return [key_list[i] for i in index], value_list
    else:
        index = [np.argmin(np.abs([i - j for j in value_position])) for i in key_position]
        # assert len(index) == len(key_list)
        # matched = zip(key_list, [value_list[i] for i in index])
        return key_list, [value_list[i] for i in index]


# def metric_reconmand(sentence, key, metric_list):
#     one_key_pattern = re.compile("\s(%s)(\s|\,|\.\()" % key, re.I)
#     key_span = [i.span() for i in one_key_pattern.finditer(sentence)]
#
#     extend_length = 0
#     for i, one_span in enumerate(key_span):
#         if one_span[0] > extend_length:
#             l_span = one_span[0] - extend_length
#         else:
#             l_span = 0
#         if one_span[1] < len(sentence) - extend_length:
#             r_span = one_span[1] + extend_length
#         else:
#             r_span = len(sentence)
#         key_span[i] = (l_span, r_span)
#
#     reconmand_list = []
#     reconmand_score = []
#     for extend_span in key_span:
#         string = "".join(list(sentence)[extend_span[0]:extend_span[1]])
#         string = [string] * len(metric_list)
#
#         scores = list(map(levenshtein_distance, string, metric_list))
#         index_s = np.argmin(np.array(scores))
#         reconmand_list.append(metric_list[index_s])
#         reconmand_score.append(scores[index_s])
#     final_index = np.argmin(np.array(reconmand_score))
#
#     return reconmand_list[final_index], reconmand_score[final_index]


def abs_extraction(recommend=True):
    filted_abs, metric_name = abs_filter()
    num_pattern = re.compile(r'\d+%|\d+\.\d+%|\d+\.\d+')
    # ' '.join(metric_name).split()
    key_pattern = re.compile("\s(%s)(\s|\,|\.\()" % ('|'.join(metric_name)), re.I)
    with open('./data/dataset_tag.json', 'r') as f:
        dataset_name = json.load(f)
    data_pattern = re.compile('(%s)' % "|".join(dataset_name), re.I)
    valued_abs = [abs_ for abs_ in filted_abs if num_pattern.search(abs_[-1]) is not None]

    extraction_results = {}
    for url, abs_ in valued_abs:
        result = {}
        lines = re.split(r'\.\s', abs_)

        informative_line = [line for line in lines
                            if num_pattern.search(line) is not None
                            and key_pattern.search(line) is not None]

        if len(informative_line) > 0:

            for index, infor_line in enumerate(informative_line):
                one_result = {"Txt": infor_line}
                key_list = [i.group()[1:-1] for i in key_pattern.finditer(infor_line)]
                num_list = [i.group() for i in num_pattern.finditer(infor_line)]
                valid_key_list, valid_value_list = string_distance(infor_line, key_list, num_list)

                # for valid_key in valid_key_list:
                #     rec_key, rec_key_score = metric_reconmand(infor_line, valid_key, metric_name)
                #     result['reconmand metric'].append(rec_key + " " + str(rec_key_score))

                if data_pattern.search(infor_line) is not None:
                    dataset_list = [i.group() for i in data_pattern.finditer(infor_line)]
                    _, valid_d_list = string_distance(infor_line, valid_value_list, dataset_list)

                    try:
                        assert len(valid_d_list) == len(valid_value_list)
                        matched = zip(valid_key_list, valid_value_list, valid_d_list)
                    except:
                        matched = zip(valid_key_list, valid_value_list)
                else:
                    matched = zip(valid_key_list, valid_value_list)

                # matched = zip(valid_key_list, valid_value_list)
                one_result['results: '] = [key_list, num_list, list(matched)]

                if recommend:
                    metric_recommend = process.extract(infor_line, metric_name, limit=4)
                    one_result["recommend metric"] = dict(metric_recommend)

                    dataset_recommend = process.extract(infor_line, dataset_name, limit=4)
                    one_result["recommend dataset"] = dict(dataset_recommend)

                if re.search(r'\s(by|than|over)\s', infor_line, re.I) is not None:
                    r_tokens = ',\/:;-=+*#()~'
                    str_list = infor_line.translate(str.maketrans(r_tokens, ' '*len(r_tokens))).split()
                    by_index = [index for index, string in enumerate(str_list)
                                if string == 'by'
                                or string == 'than'
                                or string == 'over']
                    num_index = [str_list.index(value) for value in valid_value_list]
                    min_d = [min([abs(i-j) for j in num_index]) for i in by_index]
                    if True in (np.array(min_d) < 5): one_result['Need Skip?'] = 'Yes'
                else:
                    one_result['Need Skip?'] = 'No'

                result['informative_line_%d: ' % index] = one_result
            extraction_results[url] = result
    return extraction_results


results = abs_extraction()
with open('./data/abs_sample.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=4)

