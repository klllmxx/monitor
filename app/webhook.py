#-*- coding:utf8 -*-
import json
import os
import logging
import yaml
from gevent import pywsgi
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler
from flask import request, Response, Flask, abort
from dingtalkchatbot.chatbot import DingtalkChatbot

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


def read_yaml(file_path):
    with open(file_path, "r", encoding="utf8") as f:
        return yaml.safe_load(f)


config_path = 'conf'
configfile = 'webhook.yml'
configroute = os.path.join(config_path, configfile)
config = read_yaml(configroute)
backupnum = config["Basic"]["count"]
logname = config["Basic"]["logname"]
logdir = config["Basic"]["logdir"]
webhookurl = config["Url"]["source"]
log_path = logdir
logfile = logname
logroute = os.path.join(log_path, logfile)


def Open(s):
    Path = './temp.json'
    if os.path.exists(Path):
        os.remove(Path)
    File = open(Path, "w")
    print(s, file=File)
    File.close()


def GetData():
    PostData = request.get_data()
    Data = json.loads(PostData)
    JsonData = json.dumps(Data, ensure_ascii=False, indent=4)
    return Data


logger = logging.getLogger("requests")
logger.setLevel(logging.INFO)
handler = TimedRotatingFileHandler(logroute,
                                   when="D",
                                   interval=1,
                                   backupCount=backupnum,
                                   encoding="UTF-8",
                                   utc=False,
                                   delay=False)
formatter = logging.Formatter("[%(asctime)s] - [%(levelname)s] - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(message):
    webhook = webhookurl
    wechat = DingtalkChatbot(webhook)
    wechat.send_text(msg=message, is_at_all=True)


@app.route('/', methods=['GET'])
def default_route1():
    """Default route"""
    app.logger.error("Access Not Allowed")
    abort(404)


@app.route('/wechathook', methods=['POST'])
def default_route2():
    """Default route"""
    status = GetData()['status']
    alertname = GetData()['alerts'][0]['labels']['alertname' or 'pod']
    alertmass = GetData()['alerts'][0]['annotations']['description']
    serverity = GetData()['alerts'][0]['labels']['level']
    envirom_zone = GetData()['alerts'][0]['labels']['env']
    instance = GetData()['alerts'][0]['labels']['instance']
    start_time = GetData()['alerts'][0]['startsAt']
    end_time = GetData()['alerts'][0]['endsAt']
    start_time_dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S.%fZ")
    zonetime = timedelta(hours=8)
    new_start_time = start_time_dt + zonetime
    new_start_time_dt = new_start_time.strftime("%Y-%m-%d %H:%M:%S")
    if status == "firing":
        message = str('##' + '监控小助手温馨提醒' + '##' + '\n'
                      '监控状态：%s' % status + '\n'
                      '告警主题：%s' % alertname + '\n'
                      '告警描述：%s' % alertmass + '\n'
                      '告警级别：%s' % serverity + '\n'
                      '出现问题环境：%s' % envirom_zone + '\n'
                      '实例IP地址：%s' % instance + '\n'
                      '故障发生时间：%s' % new_start_time_dt + '\n')
    elif status == "resolved":
        end_time_dt = datetime.strptime(end_time, "%Y-%m-%dT%H:%M:%S.%fZ")
        new_end_time = end_time_dt + zonetime
        new_endtime_dt = new_end_time.strftime("%Y-%m-%d %H:%M:%S")
        message = str('##' + '监控小助手温馨提醒' + '##' + '\n'
                      '监控状态：%s' % status + '\n'
                      '告警主题：%s' % alertname + '\n'
                      '告警描述：%s' % alertmass + '\n'
                      '告警级别：%s' % serverity + '\n'
                      '出现问题环境：%s' % envirom_zone + '\n'
                      '实例IP地址：%s' % instance + '\n'
                      '故障恢复时间：%s' % new_endtime_dt + '\n')
    else:
        message = str('##' + '监控小助手温馨提醒' + '##' + '\n'
                      '##' + '请检查监控网络状态' + '##' + '\n')
    send_message(message)
    return "OK", 200


@app.errorhandler(404)
def error_handler(e):
    print(e)
    return "404 Not Found: The requested URL was not found on the server.", 404


@app.after_request
def requestss(Response):
    start_code = Response.status_code
    logger.info(
        f'ip: {request.remote_addr} - Request: {request.method}  - Request_url: {request.url} status_code: {start_code}'
    )
    print(Response)
    return Response


if __name__ == '__main__':
    server = pywsgi.WSGIServer(('0.0.0.0', 7708), app)
    server.serve_forever()
