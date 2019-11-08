import json
import re
import time
import multiprocessing as mp
from urllib import request
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.keys import Keys


def read_tag():
    with open('./data/tech_tag.json', 'r') as f:
        tag_list = list(set(json.load(f)))
    return tag_list


def get_counts(driver, num_pattern):
    """
    :param driver: selenium webdriver objects
    :param num_pattern: RE pattern to extracting num only
    :return: paper counts in target domain
             - return 0, if web change to fuzzy matching
             - return 0, if web find nothing
             - return counts, if find something in exactly mode
    """
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


def s_scholar_scraper(start):
    """
    using selenium to scraping SemanticScholar data
    """
    items_per_processing = 20
    driver = webdriver.Chrome()
    num_pattern = re.compile(r'\d+')
    base_url = 'https://www.semanticscholar.org/search?'

    total_counts = {}
    for tag in tqdm(read_tag()[start*items_per_processing:(start+1)*items_per_processing]):
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
                    time.sleep(4)
                    try:
                        one_tech[str(i)] = get_counts(driver, num_pattern)
                    except:
                        one_tech[str(i)] = 'err'
                        continue
            # total_counts[tag] = one_tech
            with open('./data/papers_counts.json', 'a', encoding='utf-8') as f:
                json.dump({tag: one_tech}, f, indent=4)
        except BaseException as e:
            print(e)
            continue
    driver.close()
    return None


def s_scholar_scraper_test():
    from bs4 import BeautifulSoup
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


def collect_result(result):
    global results
    results.append(result)


if __name__ == "__main__":
    pool = mp.Pool(16)
    print(mp.cpu_count())
    for i in range(16):
        pool.apply_async(s_scholar_scraper, args=(i,), callback=collect_result)
    pool.close()
    pool.join()
    quit()
