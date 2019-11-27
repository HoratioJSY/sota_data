import re
import pickle
import json
import nltk
import time
import urllib.request
import numpy as np
from bs4 import BeautifulSoup
from tqdm import tqdm
from selenium import webdriver
from utils import Distance, AbsUtils, ContentReader, ContentProcess

title_pattern = re.compile(r'\s(for|with)\s', re.I)


class PaperData:
    """
    get data from arxiv daily update
    """
    def __init__(self, web_url=None):
        self.web_url = web_url
        self.abs_list = {}
        self.title_list = None
        self.abs_urls = None
        self.pdf_urls = None
        self.content = None
        self.title_index = {}
        self.date_index = {}

    def __get_pages(self, web_url):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) '
                                     'AppleWebKit/537.36 (KHTML, like Gecko) '
                                     'Chrome/78.0.3904.70 Safari/537.36'}
            request_ = urllib.request.Request(url=web_url, headers=headers)
            r = urllib.request.urlopen(request_, timeout=120).read()
            content = BeautifulSoup(r, features='html.parser')
        except BaseException as e:
            print(e, '\n using selenium to get pages\' content')
            driver = webdriver.Chrome()
            driver.get(web_url)
            time.sleep(8)
            content = driver.find_element_by_xpath("//*").get_attribute("outerHTML")
            content = BeautifulSoup(content, features='html.parser')
            driver.close()
        return content

    def get_title(self, url_=None, title_process=False):
        if title_process:
            if self.content is None:
                self.content = self.__get_pages(self.web_url)
            title_list = self.content.find_all("div", attrs={'class': 'list-title'})
            self.title_list = [title.get_text().strip()[7:] for title in title_list]
            return self.title_list
        elif url_ is not None:
            content = self.__get_pages(url_)
            title = content.find(class_='title').get_text().strip()[7:]

            dateline = content.find(class_='dateline').get_text().strip()[1:-1]
            return title, dateline

    def get_hyperlink(self):
        if self.content is None:
            self.content = self.__get_pages(self.web_url)
        abs_urls = self.content.find_all("a", attrs={'title': 'Abstract'})
        self.abs_urls = ['https://arxiv.org' + url['href'].strip() for url in abs_urls]
        # self.abs_urls.append('https://arxiv.org/abs/1902.01069')

        pdf_urls = self.content.find_all("a", attrs={'title': 'Download PDF'})
        self.pdf_urls = ['https://arxiv.org' + url["href"].strip() + '.pdf' for url in pdf_urls]

        return self.abs_urls, self.pdf_urls

    def get_abstract(self):
        try:
            with open('./data/saved_abs.p', 'rb') as f:
                self.abs_list, self.title_index, self.date_index = pickle.load(f)
        except:
            if self.abs_urls is None: _, _ = self.get_hyperlink()
            for url in tqdm(self.abs_urls):
                content = self.__get_pages(url)
                abs_ = content.find('blockquote', attrs={'abstract'}).get_text().strip()[11:]
                self.abs_list[url] = re.sub(r'\n', ' ', abs_)
                self.title_index[url] = content.find(class_='title').get_text().strip()[6:]
                self.date_index[url] = content.find(class_='dateline').get_text().strip()[1:-1]
            with open('./data/saved_abs.p', 'wb') as f:
                pickle.dump((self.abs_list, self.title_index, self.date_index), f)

        return self.abs_list


class Analyses(PaperData):
    """
    get information from title, abstract, paper content
     - task and method from paper title
     - metric, datasets, value from abstraction
     - table, best methods and value from paper content
    """
    def __init__(self, web_url=None):
        super(Analyses, self).__init__(web_url)

    def easy_title_process(self):
        if self.title_list is None: _ = self.get_title(title_process=True)
        results = {}
        split_patern = re.compile(r'\s(using|a|an|the|)\s|\:|a\s', re.I)
        for title in self.title_list:
            title_r = []
            try:
                tokens = nltk.word_tokenize(title)
            except:
                print(title)
                print(type(title))
                quit()
            tag = nltk.pos_tag(tokens)
            _, pos_list = zip(*tag)
            prep_index = [i for i, pos in enumerate(pos_list) if pos == 'IN']
            conj_index = [i for i, pos in enumerate(pos_list) if pos == 'CC']
            if len(prep_index) < 2 and len(conj_index) == 0:
                if 'for' in tokens:
                    title_split = title.split(' for ')
                    method = split_patern.split(title_split[0])[-1]
                    task = split_patern.split(title_split[1])[0]
                    title_r.extend(['method: ' + method, 'task: ' + task])
                elif 'with' in tokens:
                    title_split = title.split(' with ')
                    task = split_patern.split(title_split[0])[-1]
                    method = split_patern.split(title_split[1])[0]
                    title_r.extend(['method: ' + method, 'task: ' + task])
                if len(title_r) > 0:
                    results[title] = title_r
        return results

    def title_process_ed(self):
        pass

    def task_recommend(self):
        try:
            with open('./data/task_tag.json', 'r') as f:
                task = json.load(f)
        except:
            print('failed to load task tags')
            quit()

        results = self.easy_title_process()

        for key, value in results.items():
            task_p = value[1][6:].capitalize()
            task_p = [task_p] * len(task)
            scores = list(map(Distance.levenshtein_distance, task_p, task))
            index_s = np.argmin(np.array(scores))
            if scores[index_s] / len(task[index_s]) < 0.8:
                results[key].append(
                    'task recommendation: ' + task[index_s] + ' ' + str(scores[index_s] / len(task[index_s])))
            else:
                results[key].append('task recommendation: None')

        return results

    def abs_extraction(self):
        if len(self.abs_list) < 1: _ = self.get_abstract()
        total_abs = self.abs_list
        filted_abs, metric_name = AbsUtils.abs_filter(total_abs)

        num_pattern = re.compile(r'\d+%|\d+\.\d+%|\d+\.\d+')
        key_pattern = re.compile("\s(%s)(\s|\,|\.)" % ('|'.join(metric_name)), re.I)

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
                result['informative_line: '] = informative_line

                key_list = [i.group()[1:-1] for i in key_pattern.finditer(informative_line[0])]
                num_list = [i.group() for i in num_pattern.finditer(informative_line[0])]
                valid_key_list, valid_value_list = Distance.string_distance(informative_line[0], key_list, num_list)

                if data_pattern.search(informative_line[0]) is not None:
                    dataset_list = [i.group() for i in data_pattern.finditer(informative_line[0])]
                    _, valid_d_list = Distance.string_distance(informative_line[0], valid_value_list, dataset_list)

                    try:
                        assert len(valid_d_list) == len(valid_value_list)
                        matched = zip(valid_key_list, valid_value_list, valid_d_list)
                    except:
                        matched = zip(valid_key_list, valid_value_list)
                else:
                    matched = zip(valid_key_list, valid_value_list)

                # matched = zip(valid_key_list, valid_value_list)
                result['results: '] = [key_list, num_list, list(matched)]

                if re.search(r'\s(by|than|over)\s', informative_line[0], re.I) is not None:
                    r_tokens = ',\/:;-=+*#()~'
                    str_list = informative_line[0].translate(str.maketrans(r_tokens, ' ' * len(r_tokens))).split()
                    by_index = [index for index, string in enumerate(str_list)
                                if string == 'by'
                                or string == 'than'
                                or string == 'over']
                    num_index = [str_list.index(value) for value in valid_value_list]
                    min_d = [min([abs(i - j) for j in num_index]) for i in by_index]
                    if True in (np.array(min_d) < 5): result['Need Skip?'] = 'Yes'
                else:
                    result['Need Skip?'] = 'No'

                extraction_results[url] = result
        return extraction_results

    def pdf_process(self, url):

        results = {}
        for index, u in enumerate(tqdm(url)):
            content_vanity = ContentReader.arxiv_vanity_reader(u)
            with open("./data/table_key_tag.json", 'r') as f:
                key_name = json.load(f)

            if content_vanity is None:
                content_raw = ContentReader.raw_data_reader(u)
                if content_raw is not None:
                    informative_table, html_list = ContentProcess.get_informative_table(content_raw, key_name, raw_data=True)
                else:
                    informative_table = []
                    html_list = []
            else:
                informative_table, html_list = ContentProcess.get_informative_table(content_vanity, key_name)

            if len(informative_table) > 0:
                with open("./data/html/%d.html" % index, 'w', encoding='utf-8') as f:
                    f.write("\n".join(html_list))
                results[u] = {"informative table": "http://jiangsiyuan.com/table/%d" % index}
                results[u].update(informative_table)
            elif len(html_list) > 2:
                with open("./data/html/%d.html" % index, 'w', encoding='utf-8') as f:
                    f.write("\n".join(html_list))
                results[u] = {"informative table": "http://jiangsiyuan.com/table/%d" % index}
            else:
                results[u] = {"paper's table": 'no informative table'}

        return results


def get_sota_data(recent_url):
    analysis = Analyses(recent_url)
    if len(analysis.abs_list) < 1: _ = analysis.get_abstract()
    total_abs = analysis.abs_list
    filtered_abs, filtered_lines, _ = AbsUtils.abs_filter(total_abs, evidence=True)
    filtered_url, _ = zip(*filtered_abs)
    print(filtered_url)
    print('\ntotal papers: %d, useful papers: %d' % (len(total_abs), len(filtered_abs)))

    results = analysis.pdf_process(filtered_url)

    title_list = []
    date_list = []
    for u in filtered_url:
        title = analysis.title_index.get(u)
        date = analysis.date_index.get(u)

        if title is None or date is None:
            title, date = analysis.get_title(filtered_url)
            title_list.append(title)
            date_list.append(date)
        else:
            title_list.append(title)
            date_list.append(date)

    filtered_title = list(zip(["paper"]*len(title_list), title_list))
    filtered_date = list(zip(["dateline"]*len(date_list), date_list))

    i = 0
    for key, value in results.items():
        final_item = []
        final_item.append(filtered_title[i])
        final_item.append(filtered_date[i])
        results[key] = dict(final_item,
                            **{"Selected Reason": filtered_lines[i]}, **value)
        i += 1
    return results


if __name__ == '__main__':
    results = get_sota_data('https://arxiv.org/list/cs.AI/pastweek?skip=0&show=100')

    with open('./data/sample.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
