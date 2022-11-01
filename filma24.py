#!/usr/bin/env python3

from flask import Flask, Response, jsonify, url_for, abort
import json
from posixpath import split
from unittest import result
from bs4 import BeautifulSoup
from lxml import html, etree
import cloudscraper
import os, re, sys, getopt
import difflib
import requests
from time import sleep
import time
import yt_dlp

requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning)

scraper = cloudscraper.create_scraper(
	browser={
		'browser': 'chrome',
             	'platform': 'android',
             	'desktop': False
     	}
)

header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4040.128",
    "Accept": "text/html",
    "Content-Type": "text/html"
}

mp4_hosts = ['siasky', 'ipfs']
class Config:
    base_url = "https://www.filma24.ch"
    url = ''
    season = 0
    episode = 0
    media_type = ''
    title = ''
    url_retries = 0

def request(URL):
    try:
        req = requests.get(URL, headers=header, timeout=5)
        page = BeautifulSoup(req.text, "html.parser")
        return page
    except:
        return ''

def json_request(URL):
    try:
        page = requests.get(URL)
        return page.json()
    except:
        return ''

MANIFEST = {
    'id': 'org.f24io',
    'version': '1.0.0',

    'name': 'Filma 24',
    'description': 'Addon providing albanian subtitled movies and series',

    'types': ['movie', 'series'],

    'catalogs': [],

    'resources': [
        'catalog',
        {'name': 'stream', 'types': [
            'movie', 'series'], 'idPrefixes': ['tt']}
    ]
}

app = Flask(__name__)

def get_from_vidmoly(url):
    info = yt_dlp.YoutubeDL({}).extract_info(url, download=False)
    return info["url"]
    # print("moly")
    # fixedURL = url.replace("embed-", "")
    # videoID = fixedURL.replace("https://vidmoly.net/", "")
    # videoID = videoID.replace("https://vidmoly.to/", "")
    # videoID = videoID.replace(".html", "")
    # print(videoID)
    # pageHash = str(request(f"https://vidmoly.net/dl?op=download_orig&id={videoID}&mode=&hash="))
    # hash = re.findall(r'name="hash".*.value=".*"', pageHash)[0]
    # hash = re.findall(f'"([^"]*)"', hash)
    # print(hash)
    # hash = hash.pop()

    # if not hash:
    #     return None
    # print(f'https://vidmoly.net/dl?op=download_orig&id={videoID}&mode=n&hash={hash}')
    # url = f'https://vidmoly.net/dl?op=download_orig&id={videoID}&mode=n&hash={hash}'
    
    # page_with_mp4 = str(request(f'https://vidmoly.net/dl?op=download_orig&id={videoID}&mode=n&hash={hash}'))
    # try:
    #     mp4 = re.findall(r'https://.*([^"])*.mp4', page_with_mp4)[0]
    # except:
    #     mp4 = None

    # if not mp4:
    #     if Config.url_retries > 3:
    #         Config.url_retries = 0
    #         return None
    #     else:
    #         try:
    #             timeout = int(re.findall(r'*<b class="err">You have to wait[^"<b]*', page_with_mp4)[0])
    #             print("timeout", timeout)
    #             sleep(timeout)
    #         except:
    #             print("")
    #         Config.url_retries = Config.url_retries + 1
    #         get_from_vidmoly(url)
    # else:
    #     return mp4

def search():
    page = str(request(f"{Config.base_url}/search/{Config.title}"))
    page = html.fromstring(page).getroottree()
    result = page.xpath('//*[@class="row"]/div/a')

    if not result:
        print("no result")
        return ''
    
    for r in result:
        Config.url = r.attrib['href']
        if Config.media_type == "series" and 'seriale' in Config.url:
            return
        elif Config.media_type == "movie":
            return
    
    Config.url = ''

def get_video_url(iframe):
    if iframe.startswith('//'):
        iframe = "https:" + iframe

    website = iframe[8:].split(".")[0]
    mp4 = None
    if 'vidmoly' in website:
        mp4 = get_from_vidmoly(iframe)
        if mp4:
            return {
                    "url": mp4, 
                    "title": website, 
                    "behaviorHints": {
                        "notWebReady": True, 
                        "proxyHeaders": { 
                            "request": { 
                                "Referer": iframe,
                                "User-Agent": "Chrome/97" 
                            } 
                        }
                    } 
                }
        else:
            return None
    else:
        if website in mp4_hosts or iframe.endswith('.mp4'):
            mp4 = iframe
            return {
                "url": mp4, 
                "title": website, 
                "behaviorHints": {
                    "notWebReady": True, 
                    "proxyHeaders": { 
                        "request": { 
                            "Referer": iframe,
                            "User-Agent": "Chrome/97" 
                        } 
                    }
                } 
            }
        else:
            page = str(request(iframe))
            if page:
                mp4 = re.findall(r'https://.*[^"].m3u8', page)
                if not mp4:
                    mp4 = re.findall(r'https://.*[^\",]*.mp4', page)
                if not mp4:
                    mp4 = iframe
                else:
                    mp4 = mp4[0]
                return {
                    "url": mp4, 
                    "title": website, 
                    "behaviorHints": { 
                        "notWebReady": True, 
                        "proxyHeaders": { 
                            "request": { 
                                "Referer": iframe,
                                "User-Agent": "Chrome/97" 
                            } 
                        }
                    } 
                }
            else :
                return None    

def get_movie_streams():
    page = str(request(Config.url))
    page = html.fromstring(page).getroottree()
    server_list = page.xpath('//*[@class="player"]/div[1]/a')
    iframe = page.xpath('//*[@id="plx"]/p/iframe/@src')
    if not iframe:
        iframe = page.xpath('//*[@id="plx"]/p/video/source/@src')
    iframe = iframe[0]
    streams = []
    vid_url = get_video_url(iframe)
    if vid_url:
        streams.append(vid_url)
    server_list.pop(0)

    for r in server_list:
        server_url = Config.url + r.attrib['href']
        page = str(request(server_url))
        page = html.fromstring(page).getroottree()
        server_list = page.xpath('//*[@class="player"]/div[1]/a')
        iframe = page.xpath('//*[@id="plx"]/p/iframe/@src')
        if not iframe:
            iframe = page.xpath('//*[@id="plx"]/p/video/source/@src')
        iframe = iframe[0]
        vid_url = get_video_url(iframe)
        if vid_url:
            streams.append(vid_url)

    return {'streams': streams}

def get_episode_streams():
    page = str(request(Config.url))
    page = html.fromstring(page).getroottree()
    Config.season = int(Config.season) - 1
    Config.episode = int(Config.episode) - 1
    Config.url = page.xpath(f'//*[@class="row mb-5"][last()-{str(Config.season)}]/*[@class="movie-thumb col-6"][last()-{str(Config.episode)}]/a/@href')[0]
    return get_movie_streams()

def respond_with(data):
    resp = jsonify(data)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    return resp

@app.route('/manifest.json')
def addon_manifest():
    return respond_with(MANIFEST)


@app.route('/catalog/<type>/<id>.json')
def addon_catalog(type, id):
    if type not in MANIFEST['types']:
        abort(404)

    catalog = CATALOG[type] if type in CATALOG else []
    metaPreviews = {
        'metas': [
            {
                'id': item['id'],
                'type': type,
                'name': item['name'],
                'genres': item['genres'],
                'poster': METAHUB_URL.format(item['id'])
            } for item in catalog
        ]
    }
    return respond_with(metaPreviews)


@app.route('/meta/<type>/<id>.json')
def addon_meta(type, id):
    if type not in MANIFEST['types']:
        abort(404)

    def mk_item(item):
        meta = dict((key, item[key])
                    for key in item.keys() if key in OPTIONAL_META)
        meta['id'] = item['id']
        meta['type'] = type
        meta['name'] = item['name']
        meta['genres'] = item['genres']
        meta['poster'] = METAHUB_URL.format(item['id'])
        return meta

    meta = {
        'meta': next((mk_item(item)
                      for item in CATALOG[type] if item['id'] == id),
                     None)
    }

    return respond_with(meta)


@app.route('/stream/<type>/<id>.json')
def addon_stream(type, id):
    if type not in MANIFEST['types']:
        abort(404)

    Config.media_type = type
    streams = {'streams': []}
    Config.season = 1
    Config.episode = 1
    if (type == "series"):
        chunks = id.split(":")
        id = chunks[0]
        Config.season = chunks[1]
        Config.episode = chunks[2]

    imdb_data = json_request(f'https://v2.sg.media-imdb.com/suggestion/{id[0]}/{id}.json')
    Config.title = imdb_data['d'][0]['l']
    if (type == 'movie'):
        Config.title += ' ' + str(imdb_data['d'][0]['y'])
        search()
        print(Config.title)
        streams = get_movie_streams()
    elif (type == 'series'):
        search()
        print(Config.title)
        streams = get_episode_streams()
    
    return respond_with(streams)
        


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=80)
