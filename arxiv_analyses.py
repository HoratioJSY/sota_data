import re
import pickle
import json
import nltk
import numpy as np
from bs4 import BeautifulSoup
import urllib.request
from tqdm import tqdm
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

    def __get_pages(self, web_url):
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) '
                                 'AppleWebKit/537.36 (KHTML, like Gecko) '
                                 'Chrome/78.0.3904.70 Safari/537.36'}
        request_ = urllib.request.Request(url=web_url, headers=headers)
        r = urllib.request.urlopen(request_, timeout=120).read()
        content = BeautifulSoup(r, features='html.parser')
        return content

    def get_title(self):
        if self.content is None:
            self.content = self.__get_pages(self.web_url).dl
        title_list = self.content.find_all("div", attrs={'class': 'list-title'})
        self.title_list = [title.get_text().strip()[7:] for title in title_list]
        return self.title_list

    def get_hyperlink(self):
        if self.content is None:
            self.content = self.__get_pages(self.web_url).dl
        abs_urls = self.content.find_all("a", attrs={'title': 'Abstract'})
        self.abs_urls = ['https://arxiv.org' + url['href'].strip() for url in abs_urls]
        # self.abs_urls.append('https://arxiv.org/abs/1902.01069')

        pdf_urls = self.content.find_all("a", attrs={'title': 'Download PDF'})
        self.pdf_urls = ['https://arxiv.org' + url["href"].strip() + '.pdf' for url in pdf_urls]

        return self.abs_urls, self.pdf_urls

    def get_abstract(self):
        try:
            with open('./data/saved_abs.p', 'rb') as f:
                self.abs_list = pickle.load(f)
        except:
            if self.abs_urls is None: _, _ = self.get_hyperlink()
            for url in tqdm(self.abs_urls):
                content = self.__get_pages(url)
                abs_ = content.find('blockquote', attrs={'abstract'}).get_text().strip()[11:]
                self.abs_list[url] = re.sub(r'\n', ' ', abs_)
            with open('./data/saved_abs.p', 'wb') as f:
                pickle.dump(self.abs_list, f)

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
        if self.title_list is None: _ = self.get_title()
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
        # if self.abs_urls is None: _, _ = self.get_hyperlink()
        # url = self.abs_urls

        results = {}
        for u in tqdm(url):
            content_xml = ContentReader.arxiv_vanity_reader(u)
            if content_xml is None:
                continue
            else:
                with open("./data/table_key_tag.json", 'r') as f:
                    key_name = json.load(f)
                informative_table = ContentProcess.get_informative_table(content_xml, key_name)

                merged_table = {}
                for one_caption, one_table in informative_table.items():
                    merged_ = []
                    for row in one_table[0][1:]:
                        merged_.append([": ".join(i) for i in zip(one_table[0][0], row)])
                    if len(one_table[-1]) > 0:
                        merged_.extend(one_table[-1])
                    merged_table[one_caption] = merged_

            if len(merged_table) > 0:
                results[u] = merged_table
            else:
                results[u] = 'no informative table'
        return results


def get_sota_data(recent_url):
    analysis = Analyses(recent_url)
    if len(analysis.abs_list) < 1: _ = analysis.get_abstract()
    total_abs = analysis.abs_list
    filted_abs, metric_name = AbsUtils.abs_filter(total_abs)
    filted_url, _ = zip(*filted_abs)
    print('total papers in one day: %d, useful papers: %d' % (len(total_abs), len(filted_abs)))

    results = analysis.pdf_process(filted_url)
    return results


if __name__ == '__main__':
    results = get_sota_data('https://arxiv.org/list/cs.AI/recent')

    with open('./data/sample.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
