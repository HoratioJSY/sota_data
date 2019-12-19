import re
import json
import time
import sqlite3
import urllib.request
from bs4 import BeautifulSoup
from tqdm import tqdm
from selenium import webdriver


class PaperData:
    """
    get data from arxiv daily update
    """
    def __init__(self, web_url=None, iter_update=True):
        self.web_url = web_url
        self.iter_update = iter_update
        self.abs_list = {}
        self.title_list = None
        self.abs_urls = []
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

    def get_title(self, url_):
        content = self.__get_pages(url_)
        title = content.find(class_='title').get_text().strip()[7:]

        dateline = content.find(class_='dateline').get_text().strip()[1:-1]
        return title, dateline

    def get_hyperlink(self, end_iter=False):

        if self.iter_update:
            conn = sqlite3.connect('./test.db')
            c = conn.cursor()
            #  ORDER BY Date DESC
            cursor = c.execute("SELECT ID FROM LatestPaper")
            latest_id = cursor.fetchone()[0]
            print(latest_id)
            conn.close()

            while end_iter is False:
                content = self.__get_pages(self.web_url)
                abs_urls = content.find_all("a", attrs={'title': 'Abstract'})

                for u in abs_urls:
                    u_ = u['href'].strip()
                    if latest_id not in u_:
                        self.abs_urls.append('https://arxiv.org' + u_)
                    else:
                        end_iter = True
                        break

                span = [str(int(num)+50) for num in re.findall(r'\d+', self.web_url)]
                self.web_url = f"https://arxiv.org/list/cs/pastweek?skip={span[0]}&show=50"
                print(self.web_url)
        else:
            content = self.__get_pages(self.web_url)
            abs_urls = content.find_all("a", attrs={'title': 'Abstract'})
            self.abs_urls = ['https://arxiv.org' + u['href'].strip() for u in abs_urls]

        if len(self.abs_urls) > 0:
            new = self.abs_urls[0].split('/')[-1]
            conn = sqlite3.connect('./test.db')
            c = conn.cursor()
            c.execute("DELETE FROM LatestPaper")
            c.execute("INSERT INTO LatestPaper VALUES (?)", (new,))
            conn.commit()
            conn.close()

        return self.abs_urls

    def get_abstract(self):

        if len(self.abs_urls) < 1: _ = self.get_hyperlink()

        for url in tqdm(self.abs_urls):
            content = self.__get_pages(url)
            abs_ = content.find('blockquote', attrs={'abstract'}).get_text().strip()[11:]
            self.abs_list[url] = re.sub(r'\n', ' ', abs_)
            self.title_index[url] = content.find(class_='title').get_text().strip()[6:]
            self.date_index[url] = content.find(class_='dateline').get_text().strip()[1:-1]

        return self.abs_list


class SotaSelection(PaperData):
    def __init__(self, web_url=None, iter_update=True):
        super(SotaSelection, self).__init__(web_url, iter_update)

    def abs_filter(self, evidence=False, strict_mode=False):

        with open("./data/sota_tag.json", 'r') as f:
                sota_name = json.load(f)

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

    @staticmethod
    def push_database(results):
        k_pattern = re.compile(r'\d+\.[\dv]+')
        d_pattern = re.compile(r'(\s)(\d+)(\s|$)')

        mouth = ['jan', "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        mouth_dict = dict(zip(mouth, range(len(mouth))))
        m_pattern = re.compile(r'%s' % "|".join(mouth), re.I)

        conn = sqlite3.connect('./test.db')
        c = conn.cursor()

        c.execute('''CREATE TABLE IF NOT EXISTS PaperSelection
                    (ID TEXT PRIMARY KEY,
                    Paper TEXT,
                    URL TEXT,
                    Date DATE,
                    DateLine TEXT,
                    SelectedReason TEXT)''')
        data = []
        for url, value in results.items():
            date = []
            dy = [j.group(2) for j in d_pattern.finditer(value["dateline"])][-2:]
            mou = [j.group(0) for j in m_pattern.finditer(value["dateline"])][-1]
            mou = mouth_dict.get(mou.lower(), -1) + 1

            date.append(dy[-1])
            date.append(str(mou))

            if len(dy[0]) == 1:
                date.append("0" + dy[0])
            else:
                date.append(dy[0])
            date = "-".join(date)

            key_phrase = k_pattern.search(url)
            key_phrase = key_phrase.group()
            data.append((key_phrase, value["paper"], url, date, value["dateline"],
                         "<split_mark>".join(value["Selected Reason"])))

        statement = 'INSERT OR IGNORE INTO PaperSelection VALUES (?, ?, ?, ?, ?, ?)'
        conn.executemany(statement, data)
        conn.commit()
        conn.close()


if __name__ == "__main__":
    sota = SotaSelection('https://arxiv.org/list/cs/pastweek?skip=0&show=50')
    results = sota.paper_selection()
    sota.push_database(results)

    with open('./data/sample.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)