import re
import pandas as pd
import numpy as np
import json
import nltk
from arxiv_analyses import Analyses


def load():
    df = pd.read_csv('./data/Sota_Evaluations.csv')
    df = df.dropna(axis=0)
    title = df['paper']
    title = np.array(title)

    with open('./data/task_tag.json', 'r') as f:
        task = json.load(f)
        print('num of task: ', len(task))

    return title, task


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


def task_recommend():
    title, task = load()
    analyzer = Analyses()
    analyzer.title_list = title[:1000]
    results = analyzer.easy_title_process()

    for key, value in results.items():
        task_p = value[1][6:].capitalize()
        task_p = [task_p] * len(task)
        scores = list(map(levenshtein_distance, task_p, task))
        index_s = np.argmin(np.array(scores))
        if scores[index_s] / len(task[index_s]) < 0.8:
            results[key].append(
                'task recommendation: ' + task[index_s] + ' ' + str(scores[index_s] / len(task[index_s])))
        else:
            results[key].append('task recommendation: None')

    with open('./data/task_recommendation.json', 'w') as f:
        json.dump(results, f, indent=4)


# title_pattern = re.compile(r'\s(for|with)\s', re.I)
# # test, using pos for extraction
# def title_process(self):
#     if self.title_list is None: _ = self.get_title()
#     results = {}
#     for title in self.title_list:
#         title_results = []
#         if title_pattern.findall(title) is not None:
#             key_list = title_pattern.findall(title)
#             tokens = nltk.word_tokenize(title)
#             key_index = [index for index, value in enumerate(tokens) if value in key_list]
#             tag = nltk.pos_tag(tokens)
#             # print(tag)
#
#             for index in key_index:
#                 pre_words = []
#                 post_words = []
#                 for i in range(index-1, -1, -1):
#                     if tag[i][1] in ['NNP', 'JJ', 'VBD']:
#                         pre_words.append(tokens[i])
#                     else:
#                         break
#                 for j in range(index+1, len(tokens)):
#                     if tag[j][1] in ['NNP', 'JJ', 'VBD']:
#                         post_words.append(tokens[j])
#                     else:
#                         break
#
#                 if len(pre_words) > 0 and len(post_words) > 0:
#                     pre_words.reverse()
#                     title_results.append((' '.join(pre_words), ' '.join(post_words)))
#         if len(title_results) > 0:
#             results[title] = title_results
#     return results


if __name__ == "__main__":
    task_recommend()