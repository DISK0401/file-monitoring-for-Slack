# coding:utf-8
import logging.handlers
from logging import DEBUG, INFO, Formatter, StreamHandler, getLogger
from config import slack_token, allow_file_mode, allow_file_type, ng_file_type, delete_unknown_file_type
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
    illegal_file_monitoring()
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


def delete_file(file_id):
    """
    指定ファイルを削除する
    """
    header = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    payload = {
        'token': slack_token,
        'file': file_id
    }
    logger.debug("[FILES_DELETE_API_PAYLOAD] " + str(payload))
    response = requests.post(FILES_DELETE_API_URL, headers=header, params=payload)
    logger.debug("[FILES_DELETE_API_RESULT] " + str(response.json()))
    return response.json()['ok']


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
    logger.debug("[TS_TIME] from:" + (str(datetime.datetime.fromtimestamp(from_time)) if not(from_time is None) else "None") + ", to:" + (str(datetime.datetime.fromtimestamp(to_time)) if not(to_time is None) else "None"))
    response = requests.get(FILES_LIST_API_URL, headers=header, params=payload)
    result = response.json()['files']
    logger.debug("[FILE_LIST_API_RESULT] " + str(result))
    logger.info("[HIT_FILES_NUM] " + str(len(result)))
    return result


def judge_delete_target_file(file_info):
    """
    削除対象のファイルかどうかを判定する
    """
    to_delete = False

    # ファイルモードが削除対象かどうか
    if file_info['mode'] == 'snippets':
        # スニペットの場合
        if not allow_file_mode['snippets']:
            to_delete = True

    elif (file_info['mode'] == 'hosted'):
        # Slackに直接アップロードした場合
        if not allow_file_mode['hosted']:
            to_delete = True
        else:
            to_delete = is_delete_target_file_type(file_info)

    elif (file_info['mode'] == 'external'):
        # アプリ連携などでGoogle Dviveなどから取り込まれた場合
        if not allow_file_mode['external']:
            to_delete = True
        else:
            to_delete = is_delete_target_file_type(file_info)

    elif file_info['mode'] == 'docs':
        if not allow_file_mode['docs']:
            to_delete = True

    else:
        # 未知のモードの場合
        to_delete = delete_unknown_file_type
    
    return to_delete


def is_delete_target_file_type(file_info):
    """
    削除対象のファイルタイプかどうかを判定する
    """
    pretty_type = file_info['pretty_type']
    if pretty_type in ng_file_type:
        # NGリストに入っている場合は、True
        return True
    elif pretty_type in allow_file_type:
        # 許諾リストに入っている場合は、False
        return False
    else:
        # どちらにも入っていない場合は、設定に従う
        return delete_unknown_file_type


def illegal_file_monitoring():
    """
    アップロード禁止ファイルの監視
    """
    global last_execute_time
    if last_execute_time is None:
        last_execute_time = int(time.time())
        files = get_files(to_time=last_execute_time)
    else:
        now = int(time.time())
        files = get_files(from_time=last_execute_time, to_time=now)
        last_execute_time = now

    for file_info in files:
        logger.info("[FILE_INFO] " + str(file_info))
        logger.info("[FILE_CREATE_DATE] " + str(datetime.datetime.fromtimestamp(file_info['created'])))
        is_delete = judge_delete_target_file(file_info)
        logger.info("[IS_DELETE] " + str(is_delete))
        if is_delete:
            result = delete_file(file_info['id'])
            if result:
                logger.info("[FILE_DELETE_SUCCESS] ファイル名：" + file_info['name'] + ", pretty_type：" + file_info['pretty_type'])
            else:
                logger.info("[FILE_DELETE_FAILED] ファイル名：" + file_info['name'] + ", pretty_type：" + file_info['pretty_type'])


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
    interval_tm = 30
    logger.info("[interval_time] " + str(interval_tm) + "s")
    last_execute_time = None
    scheduler(interval_tm, worker, wait=True)
