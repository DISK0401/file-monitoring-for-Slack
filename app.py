# coding:utf-8
import logging.handlers
from logging import DEBUG, INFO, Formatter, StreamHandler, getLogger
from config import slack_token
import threading
import requests
import time
import datetime


# API_URL
CHANNEL_LIST_API_URL = 'https://slack.com/api/channels.list'
GROUP_LIST_API_URL = 'https://slack.com/api/groups.list'
USER_LIST_API_URL = 'https://slack.com/api/users.list'
FILES_LIST_API_URL = 'https://slack.com/api/files.list'
FILES_DELETE_API_URL = 'https://slack.com/api/files.delete'


def scheduler(interval_time, func, wait=True):
    """
    ワーカーを管理する。
    waitが
    ・Trueの場合 ：前回の実行が終了していない場合は、再度指定時間待つ。
    ・Falseの場合：前回の実行が終了していない場合は、新規スレッドで同時に実行する
    """
    base_time = time.time()
    next_time = 0
    while True:
        t = threading.Thread(target=func, args=(interval_time,))
        t.start()
        if wait:
            t.join()
        next_time = ((base_time - time.time()) % interval_time) or interval_time
        time.sleep(next_time)


def worker(interval_time):
    """
    ワーカー。
    実際に実行される関数
    """
    logger.info("[start] worker")
    logger.info("[end] worker")


def get_public_channels():
    """
    パブリックチャンネルの一覧を取得する
    """
    header = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'exclude_archived': 'true',
        'exclude_members': 'false',
        'limit': '0'
    }
    payload = {
        'token': slack_token
    }
    response = requests.get(CHANNEL_LIST_API_URL, headers=header, params=payload)
    result = response.json()['channels']
    logger.debug("[CHANNEL_LIST_API_RESULT] " + str(result))
    return result


def get_private_channels():
    """
    プライベートチャンネルの一覧を取得する
    """
    header = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'exclude_archived': 'true',
        'exclude_members': 'false',
        'limit': '0'
    }
    payload = {
        'token': slack_token
    }
    response = requests.get(GROUP_LIST_API_URL, headers=header, params=payload)
    result = response.json()['groups']
    logger.debug("[GROUP_LIST_API_RESULT] " + str(result))
    return result


def get_users():
    """
    ユーザー一覧を取得する
    """
    header = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    payload = {
        'token': slack_token
    }
    response = requests.get(USER_LIST_API_URL, headers=header, params=payload)
    result = response.json()['members']
    logger.debug("[USER_LIST_API_RESULT] " + str(result))
    return result


def get_files(from_time=None, to_time=None):
    """
    ファイル一覧を取得する
    """
    header = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    payload = {
        'token': slack_token,
        'count': 100,
        'page': 1,
    }
    if from_time:
        payload['ts_from'] = from_time
    if to_time:
        payload['ts_to'] = to_time
    logger.debug("[FILE_LIST_API_PAYLOAD] " + str(payload))
    response = requests.get(FILES_LIST_API_URL, headers=header, params=payload)
    result = response.json()['files']
    logger.debug("[FILE_LIST_API_RESULT] " + str(result))
    logger.info("[HIT_FILES_NUM] " + str(len(result)))
    return result


if __name__ == '__main__':
    logger = getLogger(__name__)
    handler_format = Formatter('[%(asctime)s][%(name)s][%(levelname)s]-%(message)s')
    fh = logging.handlers.TimedRotatingFileHandler(
        filename='log/system.log',
        when='midnight',
        encoding='utf-8',
        backupCount=20
    )
    fh.setFormatter(handler_format)
    logger.addHandler(fh)
    sh = StreamHandler()
    sh.setLevel(DEBUG)
    sh.setFormatter(handler_format)
    logger.addHandler(sh)
    logger.setLevel(DEBUG)
    logger.propagate = False
    logger.info("Start-UP")
    interval_tm = 15
    logger.info("[interval_time] " + str(interval_tm) + "s")
    scheduler(interval_tm, worker, wait=True)
