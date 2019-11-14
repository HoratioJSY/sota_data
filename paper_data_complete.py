import json
import time
import collections
import numpy as np
import pandas as pd
from urllib import request
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

df = pd.read_csv('./data/Sota_Evaluations.csv')
filtered_df = df.loc[df['paperurl'].isnull(), :]
filtered_df = filtered_df.loc[filtered_df['paper'].notnull(), :]

papers = list(set(filtered_df['paper']))
driver = webdriver.Chrome()

# use google to search papers
# for title in tqdm(papers):
#     driver.get('https://www.google.com/')
#     time.sleep(2)
#     input_s = driver.find_element_by_class_name('gLFyf')
#     input_s.clear()
#     input_s.send_keys("\"%s\"" % title)
#     input_s.send_keys(Keys.ENTER)
#     time.sleep(3)
#
#     try:
#         _ = driver.find_element_by_id('captcha-form')
#         a = input()
#         search_items = driver.find_elements_by_class_name('g')
#
#         title_url = collections.OrderedDict()
#         for element in search_items:
#             title_ = element.find_element_by_tag_name('h3').text
#             url_ = element.find_element_by_tag_name('a').get_attribute("href")
#             title_url[title_] = url_
#
#         results[title] = title_url
#
#     except:
#
#         try:
#             search_items = driver.find_elements_by_class_name('g')
#
#             title_url = collections.OrderedDict()
#             for element in search_items:
#                 title_ = element.find_element_by_tag_name('h3').text
#                 url_ = element.find_element_by_tag_name('a').get_attribute("href")
#                 title_url[title_] = url_
#
#             results[title] = title_url
#         except:
#             continue


def levenshtein_distance(string_one, string_two):
    if len(string_one) < len(string_two): return levenshtein_distance(string_two, string_one)
    # TO DO: a method to normalizing score that take no effects of ranking
    if len(string_two) == 0: return len(string_one)

    string_one = string_one.lower()
    string_two = string_two.lower()

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


def read_result(driver):
    search_items = driver.find_elements_by_class_name('search-result')

    title_url = collections.OrderedDict()
    for element in search_items:
        title_ = element.find_element_by_class_name('search-result-title').text.strip()
        url_ = element.find_element_by_tag_name('a').get_attribute("href")
        try:
            pdf_url = element.find_element_by_class_name('paper-link').get_attribute("href")
            title_url[title_] = [url_, pdf_url]
        except:
            title_url[title_] = url_
    return title_url

def get_papers(papers):
    results = {}
    for title in tqdm(papers):
        base_url = 'https://www.semanticscholar.org/search?'

        # if filtered_df.loc[filtered_df['paper']==title, 'date'].any():
        if False:
            year_ = int(filtered_df.loc[filtered_df['paper']==title, 'date'].any()[:4])
            year_url = 'year[0]=%d&year[1]=%d&' % (year_, year_)
            query = base_url + year_url + 'q=\"%s\"' % title + "&sort=relevance&fos=computer-science"
        else:
            query = base_url + 'q=\"%s\"' % title + "&sort=relevance&fos=computer-science"

        url = request.quote(query, safe="\"\';/?:@&=+$,", encoding="utf-8")
        driver.get(url)
        time.sleep(2)

        try:
            title_url = read_result(driver)
            if len(title_url) < 1:
                time.sleep(6)
                title_url = read_result(driver)
                results[title] = title_url
            else:
                results[title] = title_url
        except BaseException as e:
            print(e)
            continue

    driver.close()
    return results


def filtered_papers(results):
    for key, value in results.items():
        try:
            key_list = [key] * len(value)
            value_list = list(value.keys())
            scores = list(map(levenshtein_distance, key_list, value_list))
            index_s = np.argmin(np.array(scores))
            if scores[index_s] < 6:
                value = value_list[index_s]
                results[key] = {value: results[key][value]}
            else:
                results[key] = None
        except BaseException as e:
            print(e)
            # key_list = [key] * len(value)
            # value_list = list(value.keys())
            # print(value_list)
            # print(key_list)
            # print(key)
            # quit()
            continue
    return results


results = get_papers(papers)
with open('./data/papers_complete_test.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=4)
# with open('./data/papers_complete_test.json', 'r') as f:
#     results = json.load(f)


with open('./data/papers_complete.json', 'w', encoding='utf-8') as f:
    json.dump(filtered_papers(results), f, ensure_ascii=False, indent=4)

# filtered_df.to_csv('./data/sample.csv', index=False, sep=',')
