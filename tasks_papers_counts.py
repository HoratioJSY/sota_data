import json
import re
import time
from bs4 import BeautifulSoup
from urllib import request
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.keys import Keys


def read_tag():
    with open('./data/TechField.json', 'r') as f:
        tag_list = json.load(f)
    return tag_list


def get_counts(driver, num_pattern):
    try:
        _ = driver.find_element_by_class_name("original")
        counts = 0
    except:
        try:
            _ = driver.find_element_by_class_name("bold")
            counts = 0
        except:
            counts = driver.find_element_by_class_name("result-count").text.replace(',', '')
            counts = num_pattern.search(counts).group()
            counts = int(counts)
    return counts


def s_scholar_scraper():
    driver = webdriver.Chrome()
    num_pattern = re.compile(r'\d+')
    base_url = 'https://www.semanticscholar.org/search?'

    total_counts = {}
    for tag in tqdm(read_tag()[30:32]):
        one_tech = {}
        driver.get("https://www.semanticscholar.org/")
        time.sleep(2)
        try:
            input_s = driver.find_element_by_class_name('input')
            input_s.clear()
            input_s.send_keys("\"%s\"" % tag)
            input_s.send_keys(Keys.ENTER)
            time.sleep(3)

            total_ = driver.find_element_by_class_name("result-count").text.replace(',', '')
            total_ = num_pattern.search(total_).group()
            one_tech['total counts'] = int(total_)
            bound = [int(i.text) for i in driver.find_elements_by_class_name("bubble")]
            for i in tqdm(range(bound[0], bound[1]+1)):
                s_url = 'q=\"%s\"' % tag
                year_url = 'year[0]=%d&year[1]=%d&'%(i, i)
                url = request.quote(base_url + year_url + s_url, safe="\"\';/?:@&=+$,", encoding="utf-8")

                try:
                    driver.get(url)
                    time.sleep(1)
                    one_tech[str(i)] = get_counts(driver, num_pattern)
                except:
                    time.sleep(3)
                    try:
                        one_tech[str(i)] = get_counts(driver, num_pattern)
                    except:
                        one_tech[str(i)] = 'err'
                        continue
            total_counts[tag] = one_tech

            # buckets = driver.find_element_by_class_name("buckets")
            # years = buckets.find_elements_by_tag_name("rect")
            # for y in years:
            #     y.click()
            #     time.sleep(2)

        except BaseException as e:
            print(e)
            continue
    driver.close()
    with open('./data/papers_counts.json', 'w', encoding='utf-8') as f:
        json.dump(total_counts, f, indent=4)


def s_scholar_scraper_test():
    base_url = 'https://www.semanticscholar.org/search?'
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) '
                             'AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/78.0.3904.70 Safari/537.36'}
    # 'year[0]=2004&year[1]=2004&q="generative adversarial network"&sort=relevance'
    # q="generative%20adversarial%20network"&sort=relevance
    for tag in tqdm(read_tag()[:5]):
        s_url = 'q=\"%s\"' % tag
        print(request.quote(base_url + s_url, safe="\"\';/?:@&=+$,", encoding="utf-8"))
        request_ = request.Request(url=request.quote(base_url + s_url,
                                                     safe=";/?:@&=+$,",
                                                     encoding="utf-8"), headers=headers)
        r = request.urlopen(request_, timeout=60).read()
        content = BeautifulSoup(r, features='html.parser')
        print(content)
        total_num = content.find('div', attrs={"class": "result-count"}).get_text().strip().replace(',', '')
        print(total_num)


if __name__ == "__main__":
    s_scholar_scraper()