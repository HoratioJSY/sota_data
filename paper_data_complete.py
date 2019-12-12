import json
import time
import collections
import re
import numpy as np
import pandas as pd
from urllib import request
from tqdm import tqdm
from selenium import webdriver
from flashtext import KeywordProcessor

dataframe = pd.read_csv('./data/Sota_Evaluations.csv')


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


class Title2Link(object):
    def __init__(self, df):
        self.filtered_df = df.loc[df['paperurl'].isnull(), :]
        self.filtered_df = self.filtered_df.loc[self.filtered_df['paper'].notnull(), :]
        self.papers_list = list(set(self.filtered_df['paper']))
        self.driver = webdriver.Chrome()
        self.results = {}

    @staticmethod
    def _read_result(driver):
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

    def get_papers(self, use_date=False):
        base_url = 'https://www.semanticscholar.org/search?'
        for title in tqdm(self.papers_list):

            if self.filtered_df.loc[self.filtered_df['paper'] == title, 'date'].any() and use_date:
                year_ = int(self.filtered_df.loc[self.filtered_df['paper'] == title, 'date'].any()[:4])
                year_url = 'year[0]=%d&year[1]=%d&' % (year_, year_)
                query = base_url + year_url + 'q=\"%s\"' % title + "&sort=relevance&fos=computer-science"
            else:
                query = base_url + 'q=\"%s\"' % title + "&sort=relevance&fos=computer-science"

            url = request.quote(query, safe="\"\';/?:@&=+$,", encoding="utf-8")
            self.driver.get(url)
            time.sleep(2)

            try:
                title_url = self._read_result(self.driver)
                if len(title_url) < 1:
                    time.sleep(6)
                    title_url = self._read_result(self.driver)
                    self.results[title] = title_url
                else:
                    self.results[title] = title_url
            except BaseException as e:
                print(e)
                continue
        self.driver.close()
        return self.results

    def filtered_papers(self):
        if len(self.results) < 1: self.get_papers()
        for key, value in self.results.items():
            try:
                key_list = [key] * len(value)
                value_list = list(value.keys())
                scores = list(map(levenshtein_distance, key_list, value_list))
                index_s = np.argmin(np.array(scores))
                if scores[index_s] < 6:
                    value = value_list[index_s]
                    self.results[key] = {value: self.results[key][value]}
                else:
                    self.results[key] = None
            except BaseException as e:
                print(e)
                continue
        return self.results


class Key2Link(object):
    def __init__(self, dataframe):
        self.df = dataframe
        self.filtered_df = None
        self.results = {}
        self.filtered_results = {}
        self.driver = None
        self.replace_pattern = re.compile(r'(（|\().+?(\)|）)')
        self.author_pattern = re.compile(r'(\()([a-zA-Z\-]+\set\sal)')

    def re_raw_model(self, model):
        raw_list = [key for key in self.filtered_df['model'] if key.find(model) > -1]
        if len(raw_list) > 0:
            raw_model_name, _ = collections.Counter(raw_list).most_common(1)[0]
            return raw_model_name
        else:
            return None

    def _pre_process(self):
        if self.filtered_df is None:
            self.filtered_df = self.df.loc[self.df['paperurl'].isnull(), :]
            self.filtered_df = self.filtered_df.loc[self.filtered_df['paper'].isnull(), :]
        raw_models = list(self.filtered_df['model'])[4:]
        raw_models = [key for key in raw_models if re.search(r'^[a-zA-Z\-]+\set\sal', key) is None]
        models = [self.replace_pattern.sub(r'', keyword).strip() for keyword in raw_models]

        authors = []
        for keywords in raw_models:
            author = self.author_pattern.findall(keywords)
            if len(author) > 0:
                authors.append(author[0][-1])
            else:
                authors.append('')
        assert len(models) == len(authors)

        # dictionary for index
        task_dict = {}
        metric_dict = {}
        dataset_dict = {}
        raw_name_dict = {}

        for model in models:
            raw_name = self.re_raw_model(model)

            if raw_name is not None:
                task = list(self.filtered_df.loc[self.filtered_df['model'] == raw_name, 'task'])
                dataset = list(self.filtered_df.loc[self.filtered_df['model'] == raw_name, 'dataset'])
                metric = list(self.filtered_df.loc[self.filtered_df['model'] == raw_name, 'metric'])
                task_dict[model] = task[0]
                metric_dict[model] = metric[0]
                dataset_dict[model] = dataset
                raw_name_dict[model] = raw_name

        return models, authors, task_dict, raw_name_dict, metric_dict, dataset_dict

    @staticmethod
    def _read_results(driver, model_phrase):
        search_items = driver.find_elements_by_class_name('search-result')

        title_abs_url = collections.OrderedDict()

        index_dict = {0: 0.2, 1: 0.1, 2: 0.1}

        for index, element in enumerate(search_items):
            confidence = 0
            title_ = element.find_element_by_class_name('search-result-title').text.strip()
            url_ = element.find_element_by_tag_name('a').get_attribute("href")
            abs_ = element.find_element_by_class_name("search-result-abstract")

            try:
                abs_.find_element_by_class_name("more").click()
                abs_ = abs_.text.strip()
            except:
                abs_ = abs_.text.strip()

            if index_dict.get(index) is not None:
                confidence = index_dict.get(index)

            try:
                pdf_url = element.find_element_by_class_name('paper-link').get_attribute("href")
                title_abs_url[title_] = {"abs": abs_, 'url': [url_, pdf_url], 'confidence': confidence}
            except:
                title_abs_url[title_] = {"abs": abs_, 'url': [url_], 'confidence': confidence}

            # if title_.lower().find(model_phrase.lower()) > -1 \
            #         or abs_.lower().find(model_phrase.lower()) > -1:
            #     try:
            #         pdf_url = element.find_element_by_class_name('paper-link').get_attribute("href")
            #         title_abs_url[title_] = {"abs": abs_, 'url': [url_, pdf_url]}
            #     except:
            #         title_abs_url[title_] = {"abs": abs_, 'url': [url_]}

        return title_abs_url

    def get_papers(self, use_date=False, use_author=False, use_task=False):
        models, authors, task_dict, raw_name_dict, _, _ = self._pre_process()
        base_url = 'https://www.semanticscholar.org/search?'
        self.driver = webdriver.Chrome()

        for index, model in enumerate(tqdm(models[:100])):
            if raw_name_dict.get(model) is None: continue

            # use date to enforce search
            if use_date:
                year_ = self.filtered_df.loc[self.filtered_df['model'] == raw_name_dict.get(model), 'date'].any()
                if year_ == False:
                    year_url = 'year[0]=2010&year[1]=2019&'
                else:
                    year_url = 'year[0]=%d&year[1]=%d&' % (int(year_[0:4]), int(year_[0:4]))
            else:
                year_url = ''

            # use author to enforce search, like "chao et al."
            if use_author:
                model_phrase = model + authors[index]
            else:
                model_phrase = model

            if use_task:
                model_phrase = model_phrase + task_dict[model]

            query = base_url + year_url + 'q=\"%s\"' % model_phrase + "&sort=relevance&fos=computer-science"
            url = request.quote(query, safe="\"\';/?:@&=+$,", encoding="utf-8")

            try:
                self.driver.get(url)
                time.sleep(2)

                try:
                    _ = self.driver.find_element_by_class_name("original")
                    continue
                except:
                    try:
                        _ = self.driver.find_element_by_class_name("bold")
                        continue
                    except:
                        title_url = self._read_results(self.driver, model)
                        if len(title_url) < 1:
                            time.sleep(6)
                            title_url = self._read_results(self.driver, model)
                        if len(title_url) > 0:
                            self.results[model] = title_url
            except BaseException as e:
                print(e)
                continue
        self.driver.close()
        return self.results

    def filter_paper(self):
        if len(self.results) < 1: self.get_papers()
        _, _, task_dict, raw_name_dict, metric_dict, dataset_dict = self._pre_process()

        # model_name was preprocessed, value was a dict that included all search results
        for model_name, value in self.results.items():
            # model key words should more than 2
            if len(model_name) < 3: continue

            # key_list: paper's title in searched results
            key_list = list(value.keys())
            abs_list = [i.get("abs") for i in value.values()]
            url_list = [i.get("url") for i in value.values()]
            confidence_list = [i.get("confidence") for i in value.values()]
            assert len(key_list) == len(abs_list) == len(url_list) == len(confidence_list)

            # FlashText Processor
            value_processor = KeywordProcessor()
            dataset_processor = KeywordProcessor()
            task_procrssor = KeywordProcessor()
            keyword_processor = KeywordProcessor()

            if len(key_list) == 1:
                self.filtered_results[model_name] = {'confidence': 'only one results', key_list[0]: url_list[0]}
            else:
                # continue
                value_processor.add_keywords_from_list(re.findall(r'\d+\.\d+', str(metric_dict.get(model_name))))
                dataset_processor.add_keywords_from_list(dataset_dict.get(model_name))
                task_procrssor.add_keyword(task_dict.get(model_name))
                keyword_processor.add_keyword(model_name)

                # len(key_list) are num of searched results
                for index in range(len(key_list)):
                    confidence = confidence_list[index]

                    v = value_processor.extract_keywords(key_list[index] + abs_list[index])
                    d = dataset_processor.extract_keywords(key_list[index] + abs_list[index])
                    t = task_procrssor.extract_keywords(key_list[index] + abs_list[index])
                    k = keyword_processor.extract_keywords(key_list[index] + abs_list[index])

                    if len(v) > 0: confidence += 0.4
                    if len(d) > 0: confidence += 0.3
                    if len(k) > 0: confidence += 0.2
                    if len(t) > 0: confidence += 0.1

                    if confidence > 0.2:
                        self.filtered_results[model_name] = {'confidence': confidence, key_list[index]: url_list[index]}

        return self.filtered_results


if __name__ == '__main__':
    # T2L = Title2Link(dataframe)
    # results = T2L.get_papers()
    #
    # with open('./data/papers_complete_test.json', 'w', encoding='utf-8') as f:
    #     json.dump(results, f, ensure_ascii=False, indent=4)
    #
    # total_results = T2L.filtered_papers()
    #
    # with open('./data/papers_complete.json', 'w', encoding='utf-8') as f:
    #     json.dump(total_results, f, ensure_ascii=False, indent=4)

    K2L = Key2Link(dataframe)
    # results = K2L.get_papers(use_date=True)
    # with open('./data/papers_complete_test.json', 'w', encoding='utf-8') as f:
    #     json.dump(results, f, ensure_ascii=False, indent=4)

    with open('./data/papers_complete_test.json', 'r') as f:
        results = json.load(f)
    K2L.results = results

    total_results = K2L.filter_paper()

    with open('./data/papers_complete.json', 'w', encoding='utf-8') as f:
        json.dump(total_results, f, ensure_ascii=False, indent=4)

    # filtered_df.to_csv('./data/sample.csv', index=False, sep=',')
