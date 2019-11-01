import re
import numpy as np
import json


class Distance(object):
    def __init__(self):
        pass

    @staticmethod
    def levenshtein_distance(string_one, string_two):
        if len(string_one) < len(string_two): return Distance.levenshtein_distance(string_two, string_one)
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

    @staticmethod
    def string_distance(string, key_list, value_list):
        key_position = sorted(list(set([np.mean(i.span()) for key in key_list
                                        for i in re.finditer(key, string)])))
        value_position = sorted(list(set([np.mean(i.span()) for value in value_list
                                          for i in re.finditer(value, string)])))

        if len(key_list) >= len(value_list):
            index = [np.argmin(np.abs([i - j for j in key_position])) for i in value_position]
            return [key_list[i] for i in index], value_list
        else:
            index = [np.argmin(np.abs([i - j for j in value_position])) for i in key_position]
            return key_list, [value_list[i] for i in index]


class AbsUtils(object):
    def __init__(self):
        pass

    @staticmethod
    def abs_filter(total_abs):

        try:
            with open("./data/metric.json", 'r') as f:
                metric_name = json.load(f)
        except:
            print('failed to load metric tags')
            quit()

        token_list = ' '.join(metric_name).lower().translate(str.maketrans("（）()", "    ")).split()

        filter_pattern = re.compile(r'\s(%s)\s' % ('|'.join(token_list)), re.I)
        filted_abs = [(url_, abs_) for url_, abs_ in total_abs.items() if filter_pattern.search(abs_) is not None]
        print('filtered: ', len(filted_abs))
        return filted_abs, metric_name