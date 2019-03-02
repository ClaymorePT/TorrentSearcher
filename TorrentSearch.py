#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor, wait
import requests
from lxml import html
from lxml import etree
import re
import os
import sys
import signal

from MagnetParser import MergeMagnetLinks

torrents_found = {}
process_pool = ThreadPoolExecutor(max_workers=os.cpu_count()+1)

md5_hash_re = re.compile(r"([a-fA-F\d]{32,64})")
magnet_md5_hash_re = re.compile(r":([a-fA-F\d]{16,64})")
#tr_node.xpath('//*[child::*[@class="detName"]]')
#print(etree.tostring(details_node, pretty_print=True).decode())


#Print Order in the end
print_order = set(("website", "title", "date", "seeders", "leechers", "magnet_link", "torrent_link", "age"))

#Don't print these Info Fields in the end
dont_print = set(("website", "hash", "torrent_link", "magnet_link"))

# Requests User-Agent
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_4) AppleWebKit/603.1.30 (KHTML, like Gecko) Version/10.1 Safari/603.1.30',
}

search_str = None

def handler(signum, frame):
    if search_str:
        PrintAllInfo()
        print("Operation Canceled by user")
        exit()

signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)


def PrintAllInfo():
    if search_str:
        for torrent_hash in torrents_found:
            print("#"*120)
            print("Torrent Hash {}".format(torrent_hash))
            magnet_links = []
            for location in torrents_found[torrent_hash]["locations"]:
                magnet_links.append(location['magnet_link'])
            merged_magnet_link = MergeMagnetLinks(search_str, magnet_links)
            print("  Merged Magnet: {}".format(merged_magnet_link))
            for location in torrents_found[torrent_hash]["locations"]:
                print("  website: {}".format(location["website"]))
                for key in (print_order - dont_print):
                    if key in location and location[key] != None:
                      print("    {}: {}".format(key, location[key]))
            print("")


def CheckWordsInTitle(title, words):
    assert type(title) is str, "from_web expected to be str"
    assert type(words) is list, "words expected to be list"
    assert sum((type(word) is not str for word in words)) == 0, "there is a word which is not str"

    title = title.lower()
    for word in words:
        if word.lower() not in title:
            return False
    return True


def AddTorrentInfo(from_web, torrent_details):
    global torrents_found
    assert type(from_web) is str, "from_web expected to be str"
    assert from_web != "", "from_web expected to be != ''"
    assert type(torrent_details) is dict, "torrent_details is expected to be dict"
    assert "hash" in torrent_details, "torrent_details has no hash key"
    assert "magnet_link" in torrent_details, "torrent_details has no magnet_link key"

    #lets create a torrent entry, to be added to the results
    location = {
            "website": from_web,
            "magnet_link": None,
            "title": None,
            "seeders": None,
            "leechers": None,
            "torrent_link": None,
            "date": None,
        }
    location.update(torrent_details)
    # Lets remove useless characters
    if location['title']:
        title = location['title'].strip("\n\r\t\0") # Special characters
        title = title.lstrip() # Spaces before
        title = title.rstrip() # Spaces after
        location['title'] = title

    # The torrent hash will be used as the key for the torrent
    torrent_hash = location['hash']

    # If the torrent entry does not exist, create one
    if torrent_hash not in torrents_found:
        torrents_found[torrent_hash] = {"locations": [location]}
        print("Added new torrent from {:s} with hash {:s}".format(from_web, torrent_hash))
    # If the torrent entry exists, update with a new torrent location
    else:
        torrents_found[torrent_hash]["locations"].append(location)
        print("Updated torrent {:s} details with location {:s}".format(torrent_hash, from_web))



def SearchPirateBay(search_str):
    proxybay_url = 'https://proxybay.one/'
    piratebay_proxys = []

    # Just a helper to order the proxy list, based in its status and response speed
    def proxy_elem(proxy):
        if proxy["status"] == 'down':
            return 0xFFFFFFFF
        try:
            return float(proxy["speed"])
        except ValueError:
            return 0xFFFFFFFF

    #Gets the torrent details
    def get_torrent_details(proxy_link, torrent_link):
        if 'https://' not in torrent_link:
          torrent_link = 'https://{:s}{:s}'.format(proxy_link, torrent_link)
        print(torrent_link)
        details_node = html.fromstring(requests.get(torrent_link, headers=headers).content).xpath('//div[@id="details"]')[0]
        magnet_node = details_node.xpath('//div[@class="download"]/a')[0]
        dl_col2 = list(details_node.xpath('//dl[@class="col2"]')[0])

        hash = re.findall(md5_hash_re, etree.tostring(dl_col2[12]).decode())[0]
        return {
            "magnet_link": magnet_node.get('href'),
            "hash": hash.upper(),
            "seeders": dl_col2[5].text,
            "leechers": dl_col2[7].text
        }


    # Searches for a torrent in a proxy
    def search_proxy(proxy_link, search_str):
            search_words = search_str.split(sep=" ")
            search_str = "https://{:s}/search/{:s}/0/3/0".format(proxy_link, search_str.replace(" ", "%20"))
            print("Searching in PirateBay Proxy: {:s} -> {:s}".format(proxy_link, search_str))
            tr_nodes = html.fromstring(requests.get(search_str, headers=headers).content).xpath(
                '//div[@class="detName"]/a[@class="detLink"]')
            for torrent_node in tr_nodes:
                try:
                    torrent_link = torrent_node.get('href')
                    torrent_title = torrent_node.get('title')
                    if not CheckWordsInTitle(torrent_title, search_words):
                        continue
                    torrent_details = get_torrent_details(proxy_link, torrent_link)
                    torrent_details.update({"title": torrent_title})
                    AddTorrentInfo(proxy_link, torrent_details)
                except Exception as ex:
                    print(  "Exception when getting data from Piratebay proxy {:s}\n"
                            "Reason: {:s}".format(proxy_link, str(ex)))

    try:
        root = html.fromstring(requests.get(proxybay_url, headers=headers).content)
        #print(etree.tostring(root, pretty_print=True).decode())
        pendent = []
        for node in root.xpath('//table[@id="proxyList"]/tr'):
            site_node = node.xpath('./td[@class="site"]/a')[0]
            status_node = node.xpath('./td[@class="status"]/img')[0]
            speed_node = node.xpath('./td[@class="speed"]')[0]
            #(site_node.text, site_node.get('href'), status_node.get('alt'), speed_node.text)
            piratebay_proxys.append({"site": site_node.text,
                                     "proxy_link": site_node.get('href'),
                                     "status": True if status_node.get('alt') == 'up' else False,
                                     "speed": speed_node.text})

        #Hardcoded to search only on the best 5 available piratebay proxies
        for proxy in sorted(piratebay_proxys, key=proxy_elem)[0:5]:
            #if proxy['status']:
            pendent.append(process_pool.submit(search_proxy, proxy['site'], search_str))
        wait(pendent)

    except Exception as ex:
        raise Exception("Failed to search torrent from PirateBay\n"
                        "Reason: {:s}".format(str(ex)))


#Not Working... website relies on javascript to construct the magnet link
def SearchZooqle(search_str):
    search_words = search_str.split(sep=" ")
    search_str = "https://zooqle.com/search?q={:s}&s=dt&v=t&sd=d&fmt=rss".format(search_str.replace(" ", "%20"))
    print("Searching in Zooqle.com -> {:s}".format(search_str))

    root = etree.XML(requests.get(search_str, headers=headers).content)
    # print(etree.tostring(root, pretty_print=True).decode())
    for node in root.findall('.//item'):
        try:
            #print(etree.tostring(node, pretty_print=True).decode())
            torrent_title = node.find('title').text
            if not CheckWordsInTitle(torrent_title, search_words):
                continue
            torrent_details = {
                "title": torrent_title,
                "date": node.find('pubDate').text,
                "torrent_link": node.find('enclosure', namespaces={
                    'torrent': "https://zooqle.com/xmlns/0.1/index.xmlns"}).get('url'),
                "magnet_link": node.find('torrent:magnetURI', namespaces={
                    'torrent': "https://zooqle.com/xmlns/0.1/index.xmlns"}).text,
                "seeders": node.find('torrent:seeds', namespaces={
                    'torrent': "https://zooqle.com/xmlns/0.1/index.xmlns"}).text,
                "leechers": node.find('torrent:peers', namespaces={
                    'torrent': "https://zooqle.com/xmlns/0.1/index.xmlns"}).text,
                "hash": node.find('torrent:infoHash', namespaces={
                    'torrent': "https://zooqle.com/xmlns/0.1/index.xmlns"}).text.upper(),
                "verified": node.find('torrent:verified', namespaces={
                    'torrent': "https://zooqle.com/xmlns/0.1/index.xmlns"}).text,
            }
            AddTorrentInfo("https://zooqle.com", torrent_details)
        except Exception as ex:
            print("SearchZooqle Exception: {:s}".format(str(ex)))




# def SearchTorrentz2(search_str):
#     search_str = "https://torrentz2.eu/feed?f={:s}".format(search_str.replace(" ", "+"))
#     print(search_str)
#
#     root = etree.XML(requests.get(search_str).content)
#     #print(etree.tostring(root, pretty_print=True).decode())
#     for node in root.findall('.//item'):
#         #print(etree.tostring(node, pretty_print=True).decode())
#         title = node.find('title').text
#         link = node.find('link').text
#         pub_date = node.find('pubDate').text
#         description = node.find('description').text
#         hash = description[description.find("Hash: ")+len("Hash: "):]
#         print()
#         print(title)
#         print(link)
#         print(pub_date)
#         print(hash.upper())



def SearchMonoNova(search_str):
    search_words = search_str.split(sep=" ")
    search_str = "https://monova.org/search?term={:s}&sort=1&cat=-1".format(search_str.replace(" ", "+"))
    print("Searching in MonoNova.org -> {:s}".format(search_str))

    def get_torrent_details(link):
        magnet_node = None
        details_node = None
        torrent_node = None

        root = html.fromstring(requests.get(link, headers=headers).content)
        res = root.xpath('//a[@id="download-file"]')
        #print(etree.tostring(res, pretty_print=True).decode())
        if len(res) != 0:
            magnet_node = res[0].get("href")
        else:
            raise Exception("Magnet does not exist.")

        res = root.xpath('//a[@id="download-magnet"]')
        if len(res) != 0:
            torrent_node = res[0].get("href")

        res = root.xpath('//table[@class="general-table"]/tbody')
        if len(res) != 0:
            details_node = res[0]

        date = None
        for tr_node in details_node.xpath('.//tr'):
            td_nodes = tr_node.xpath('./td')
            if td_nodes[0].text == "Added:":
                date = td_nodes[1].text
        #print(magnet_node.get('href'))
        #exit(0)

        torrent_details = {
            "torrent_link": torrent_node,
            "magnet_link": magnet_node,
            "date": date,
            "hash": re.findall(magnet_md5_hash_re, magnet_node.upper())[0],
        }
        return torrent_details

    root = html.fromstring(requests.get(search_str, headers=headers).content)
    #print(etree.tostring(root, pretty_print=True).decode())
    for node in root.xpath('//td[@class="torrent_name"]/a'):
        try:
            #print(etree.tostring(node, pretty_print=True).decode())
            torrent_title = node.text
            #print("link:", node.get('href'))
            #print("node.text:", node.text)
            if not CheckWordsInTitle(torrent_title, search_words):
                continue
            link = node.get('href')
            if link[0:len("//monova.org/")] == "//monova.org/":
                link = "https:" + link
            else:
                continue #ignore links from other domains
            torrent_details = get_torrent_details(link)
            torrent_details.update({"title": torrent_title})
            AddTorrentInfo("https://monova.org", torrent_details)
        except Exception as ex:
            print("SearchMonoNova Exception: {:s}".format(str(ex)))




def SearchLimeTorrents(search_str):
    search_words = search_str.split(sep=" ")
    search_str = "https://www.limetorrents.cc/searchrss/{:s}/".format(search_str)
    print("Searching in LimeTorrents.cc -> {:s}".format(search_str))

    def get_torrent_details(torrent_link):
        root = html.fromstring(requests.get(torrent_link, headers=headers).content)
        seeders_node = root.xpath('//span[@class="greenish"]')[0]
        leechers_node = root.xpath('//span[@class="reddish"]')[0]
        magnet_node = root.xpath('//a[contains(@href,"magnet:")]')[0]
        return {
            "hash": re.findall(magnet_md5_hash_re, magnet_node.get('href'))[0],
            "seeders" : re.findall(r"([\d]+)", seeders_node.text)[0],
            "leechers": re.findall(r"([\d]+)", leechers_node.text)[0],
            "magnet_link": magnet_node.get('href'),
        }

    root = etree.XML(requests.get(search_str, headers=headers).content)
    #print(etree.tostring(root, pretty_print=True).decode())
    for node in root.findall('.//item'):
        try:
            # print(etree.tostring(node, pretty_print=True).decode())
            torrent_title = node.find('title').text
            if not CheckWordsInTitle(torrent_title, search_words):
                continue
            date = node.find('pubDate').text
            link = node.find('link').text
            torrent_link = node.find('enclosure').get('url')
            torrent_details = get_torrent_details(link)
            torrent_details.update({
                "title": torrent_title,
                "date": date,
                "torrent_link": torrent_link,
                })
            #print(torrent_details)
            AddTorrentInfo("https://www.limetorrents.cc", torrent_details)
        except Exception as ex:
            print("SearchLimeTorrents Exception: {:s}".format(str(ex)))



def SearchBittorrent_am(search_str):
    search_words = search_str.split(sep=" ")
    search_str = "https://bittorrent.am/search.php?kwds={:s}&cat=7&x=0&y=0".format(search_str.replace(" ", "+"))
    print("Searching in bittorrent.am -> {:s}".format(search_str))

    def get_torrent_details(torrent_link):
        root = html.fromstring(requests.get(torrent_link, headers=headers).content)
        hash_node = root.xpath('//td[@class="table"]//tr[child::*[contains(text(), "Hash:")]]/td')[2]
        torrent_node = root.xpath('//td[@class="table"]//a[@id="torfile"]')[0]
        magnet_node = root.xpath('//td[@class="table"]//a[contains(@href, "magnet:")]')[0]
        return {
            "hash": hash_node.text,
            "torrent_link": torrent_node.get('href'),
            "magnet_link": magnet_node.get('href'),
        }

    root = html.fromstring(requests.get(search_str, headers=headers).content)
    #print(etree.tostring(root, pretty_print=True).decode())
    for node in root.xpath('//table[@class="torrentsTable"]/tr[@class="r"]/td/a[contains(@href,"download-torrent")]'):
        try:
            #print(etree.tostring(node, pretty_print=True).decode())
            torrent_title = node.text
            if not CheckWordsInTitle(torrent_title, search_words):
                continue
            torrent_link = "https://bittorrent.am{:s}.html".format(node.get('href'))
            torrent_details = get_torrent_details(torrent_link)
            torrent_details.update({"title": torrent_title})
            AddTorrentInfo("https://bittorrent.am", torrent_details)
        except Exception as ex:
            print("SearchBittorrent_am Exception: {:s}".format(str(ex)))


def SearchBTDig(search_str):
    search_words = search_str.split(sep=" ")
    search_str = "https://btdig.com/search?order=0&q={:s}".format(search_str.replace(" ", "+"))
    print("Searching in BTDig.com -> {:s}".format(search_str))

    def get_torrent_details(torrent_link):
        root = html.fromstring(requests.get(torrent_link, headers=headers).content)
        table_body_node = root.xpath('//table')[1]
        magnet_node = table_body_node.xpath('./tr')[2].xpath('./td[2]/div/a')[0]
        name_node = table_body_node.xpath('./tr')[3].xpath('./td[2]')[0]
        size_node = table_body_node.xpath('./tr')[4].xpath('./td[2]')[0]
        age_node = table_body_node.xpath('./tr')[5].xpath('./td[2]')[0]
        files_node = table_body_node.xpath('./tr')[6].xpath('./td[2]')[0]

        if not CheckWordsInTitle(name_node.text, search_words):
            return None
        return {
          'title': name_node.text,
          "magnet_link": magnet_node.get("href"),
          "size": size_node.text,
          "files": files_node.text,
          "age": age_node.text,
          "hash": re.findall(magnet_md5_hash_re, magnet_node.get("href").upper())[0],
        }

    root = html.fromstring(requests.get(search_str, headers=headers).content)
    #print(etree.tostring(root, pretty_print=True).decode())
    for row in root.xpath('//div[@class="one_result"]'):
        try:
            torrent_node = row.xpath('.//div[@class="torrent_name"]/a')[0]
            #print(etree.tostring(torrent_node, pretty_print=True).decode())
            torrent_link = torrent_node.get('href')
            torrent_details = get_torrent_details(torrent_link)
            if torrent_details:
                AddTorrentInfo("https://btdig.com", torrent_details)

        except Exception as ex:
            print("SearchBTDig Exception: {:s}".format(str(ex)))


def main():
    global search_str
    if (len(sys.argv) <= 1):
        print("Example: \n ./thisExec Stuff to Search")
        exit(0)

    search_str = " ".join(sys.argv[1:])
    print("Search String: ", search_str)
    active_sites = (SearchPirateBay, SearchBittorrent_am, SearchLimeTorrents, SearchBTDig)
    # SearchZooqle, SearchMonoNova, 
    try:
        futs = []
        for site in active_sites:
            futs.append(process_pool.submit(site, search_str))
        wait(futs, timeout=30)
        for f in futs:
            f.cancel()
        for f in futs:
            if type(f.exception()) not in (SystemExit, type(None)):
                print("Exception: ", str(f.exception()))
    except Exception as ex:
        print("Exception: ", str(ex))


    PrintAllInfo()
    exit(0)
