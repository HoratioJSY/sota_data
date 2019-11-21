import re
import pickle
import json
import time
import urllib.request
from bs4 import BeautifulSoup
from tqdm import tqdm
from selenium import webdriver


class PaperData:
    """
    get data from arxiv daily update
    """
    def __init__(self, web_url=None):
        self.web_url = web_url
        self.abs_list = {}
        self.title_list = None
        self.abs_urls = None
        self.content = None
        self.title_index = {}
        self.date_index = {}

    def __get_pages(self, web_url):

        # if arxiv daily update return Err403,try to use selenium
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
        return self.abs_urls

    def get_abstract(self):
        try:
            with open('./data/saved_abs.p', 'rb') as f:
                self.abs_list, self.title_index, self.date_index = pickle.load(f)
        except:
            if self.abs_urls is None: _ = self.get_hyperlink()
            for url in tqdm(self.abs_urls):
                content = self.__get_pages(url)
                abs_ = content.find('blockquote', attrs={'abstract'}).get_text().strip()[11:]
                self.abs_list[url] = re.sub(r'\n', ' ', abs_)
                self.title_index[url] = content.find(class_='title').get_text().strip()[6:]
                self.date_index[url] = content.find(class_='dateline').get_text().strip()[1:-1]
            with open('./data/saved_abs.p', 'wb') as f:
                pickle.dump((self.abs_list, self.title_index, self.date_index), f)

        return self.abs_list


class SotaSelection(PaperData):
    def __init__(self, web_url=None):
        super(SotaSelection, self).__init__(web_url)

    def abs_filter(self, evidence=False, strict_mode=True):

        try:
            with open("./data/sota_tag.json", 'r') as f:
                sota_name = json.load(f)
        except BaseException as e:
            print('failed to load sota tags\n', e)
            quit()

        if strict_mode:
            sota_name = []

        sota_name.extend(['sota', 'state(\s|-)of(\s|-)the(\s|-)art'])

        filter_pattern = re.compile(r'\s(%s)\s' % ('|'.join(sota_name)), re.I)
        filtered_abs = []
        filtered_lines = []

        # whether we should output evidence lines that filtering abstract
        if evidence:
            for url_, abs_ in self.abs_list.items():
                lines = re.split(r'\.\s', abs_)
                evidence_line = [line for line in lines if filter_pattern.search(line) is not None]
                if len(evidence_line) > 0:
                    filtered_abs.append((url_, abs_))
                    filtered_lines.append(evidence_line)
            assert len(filtered_abs) == len(filtered_lines)

            return filtered_abs, filtered_lines
        else:
            filtered_abs = [(url_, abs_) for url_, abs_ in self.abs_list.items() if filter_pattern.search(abs_) is not None]
            return filtered_abs

    def paper_selection(self):
        if len(self.abs_list) < 1: _ = self.get_abstract()
        filtered_abs, filtered_lines = self.abs_filter(evidence=True)
        filtered_url, _ = zip(*filtered_abs)
        print('\ntotal papers: %d, useful papers: %d' % (len(self.abs_list), len(filtered_abs)))

        title_list = []
        date_list = []
        results = {}
        for u in filtered_url:
            title = self.title_index.get(u)
            date = self.date_index.get(u)

            if title is None or date is None:
                title, date = self.get_title(filtered_url)
                title_list.append(title)
                date_list.append(date)
            else:
                title_list.append(title)
                date_list.append(date)

        for i in range(len(filtered_url)):
            content = {}
            content["paper"] = title_list[i]
            content["dateline"] = date_list[i]
            content["Selected Reason"] = filtered_lines[i]
            results[filtered_url[i]] = content
        return results


if __name__ == "__main__":
    sota = SotaSelection('https://arxiv.org/list/cs/pastweek?skip=0&show=100')
    results = sota.paper_selection()

    with open('./data/sample.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)