#!/usr/bin/env python3
from flask import Flask, escape, request, jsonify
import json
import time
from datetime import datetime
from datetime import timedelta
import sqlalchemy
from sqlalchemy.orm import sessionmaker, scoped_session
# from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, JSON
import redis
import pickle

# pool = redis.ConnectionPool(host='localhost', port=6379, decode_responses=True) # will decode error
# r = redis.Redis(connection_pool=pool)
# r = redis.StrictRedis(host='localhost', port=6379, db=0)
pool = redis.ConnectionPool(host='localhost', port=6379)
r = redis.Redis(connection_pool=pool)

engine = sqlalchemy.create_engine('postgresql://server:justdoit@127.0.0.1:5432/server', pool_size=2046, max_overflow=0)  # nopep8
# base = declarative_base(engine)
# inspect = sqlalchemy.inspect(engine)
base = declarative_base()
session_factory = sessionmaker(bind=engine)


class Watchdog(base):
    __tablename__ = 'watchdog'
    id = Column(Integer, primary_key=True)
    hostname = Column(String(64), nullable=True)
    data = Column(JSON, nullable=True)
    update_time = Column(DateTime, nullable=True)
    session = scoped_session(session_factory)

    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.hostname = kwargs.get('hostname')
        self.data = kwargs.get('data')
        self.update_time = kwargs.get('update_time')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self.session.commit()  # nopep8
        except Exception as e:
            print("{}, {}".format(self.__tablename__, e))
            self.session.rollback()
        self.session.close()

    def add(self, hostname=None, data=None):
        if hostname:
            new = Watchdog(hostname=hostname, data=data,
                           update_time=datetime.now())
            self.session.add(new)
            return new.id

    def searchpid(self, hostname=None, pid=None, from_date=datetime.now()-timedelta(30)):
        if hostname and pid:
            query_results = self.session.query(Watchdog).filter(
                (Watchdog.hostname == hostname) | (Watchdog.update_time > from_date)).all()
            if query_results:
                for q in query_results:
                    json_data = json.loads(q.data)
                    gpu_list = list(json_data.get('gpu'))
                    for g in gpu_list:
                        gl = g.split(':')
                        new_gl = list()
                        for l in gl:
                            new_l = l.strip()
                            if len(new_l) > 0:
                                new_gl.append(new_l)
                        if len(new_gl) > 0:
                            spid = str(new_gl[0])
                        else:
                            spid = None
                        if spid == pid:
                            return gpu_list
            return None


class WatchdogLog(base):
    __tablename__ = 'watchdoglog'
    id = Column(Integer, primary_key=True)
    hostname = Column(String(64), nullable=True)
    pid = Column(Integer, nullable=True)
    path = Column(String(1024), nullable=True)
    update_time = Column(DateTime, nullable=True)
    session = scoped_session(session_factory)

    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.hostname = kwargs.get('hostname')
        self.pid = kwargs.get('pid')
        self.path = kwargs.get('path')
        self.update_time = kwargs.get('update_time')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self.session.commit()  # nopep8
        except Exception as e:
            print("{}, {}".format(self.__tablename__, e))
            self.session.rollback()
        self.session.close()

    def add(self, hostname=None, pid=None, path=None):
        if hostname:
            new = WatchdogLog(hostname=hostname, pid=pid, path=path,
                              update_time=datetime.now())
            self.session.add(new)
            return new.id

    def searchpid(self, hostname=None, pid=None):
        if hostname and pid:
            query_results = self.session.query(WatchdogLog).filter(
                (WatchdogLog.hostname == hostname) | (WatchdogLog.pid == pid)).first()
            if query_results:
                result_list = list()
                result_list.append(query_results.path)
                return result_list

            return None


app = Flask('watchdog')

PASSWORD = '123456'
# DATABASE = dict() # duplicated


def _status(value=None):
    if not value:
        result = {'status': False}
    else:
        result = {'status': str(value)}
    return jsonify(result)


@app.route('/hello/<name>')
def helloworld(name):
    return 'Hello {}'.format(escape(name))


@app.route('/ping/<num>')
def ping(num):
    # test the spider is alive
    try:
        ping_num = int(escape(num))
    except ValueError:
        return _status()

    return str(ping_num + 1)


# {
#   "passwd": "123456",
#   "gpu": ["null"],
#   "hostname": "jay-Vostro-3881",
#   "net": {"virbr0": "192.168.122.1", "enp3s0": "null", "wlp4s0": "192.168.31.103", "lo": "127.0.0.1"},
#   "mem": {"total": "8.1 GB", "used": "3.9 GB"},
#   "swap": {"used": "37.0 MB", "total": "2.1 GB"},
#   "cpu": {"idle": 0.9702536, "interrupt": 0.0, "user": 0.008961169, "temp": 27.8, "nice": 0.0, "system": 0.020785267},
#   "other": {"uptime": "0 day 4 hour 50 minutes 8 sec", "nowtime": "xxxxx"}
# }

@app.route('/update', methods=['POST'])
def update_info():
    content_type = request.headers.get('Content-Type')
    if (content_type == 'application/json'):
        json_data = request.json
        # print(json)
        if str(json_data.get('password')) != PASSWORD:
            print(json_data.get('password'))
            return _status()

        tmp_dict = dict()
        gpu_list = json_data.get('gpu')
        gpu_list = gpu_list.replace('"', '')
        if not gpu_list or len(gpu_list) == 0:
            gpu_list = ['null']
        else:
            gpu_list = gpu_list.strip('][').split(', ')
        hostname = str(json_data.get('hostname'))
        net_dict = json.loads(json_data.get('net'))
        mem_dict = json.loads(json_data.get('mem'))
        swap_dict = json.loads(json_data.get('swap'))
        cpu_dict = json.loads(json_data.get('cpu'))
        other_dict = json.loads(json_data.get('other'))

        tmp_dict['gpu'] = gpu_list
        tmp_dict['hostname'] = hostname
        tmp_dict['net'] = net_dict
        tmp_dict['mem'] = mem_dict
        tmp_dict['swap'] = swap_dict
        tmp_dict['cpu'] = cpu_dict
        tmp_dict['other'] = other_dict
        # global DATABASE
        # DATABASE[hostname] = tmp_dict
        r.set(hostname, pickle.dumps(tmp_dict), ex=60)
        # print(len(DATABASE))
        with Watchdog() as wd:
            wd.add(hostname=hostname, data=json.dumps(tmp_dict))

        with WatchdogLog() as wdl:
            for g in gpu_list:
                if ':' in g:
                    g_split_list = g.split(':')
                    # print(g_split_list)
                    pid = g_split_list[0].strip()
                    pid = pid.replace('"', '')
                    if not pid:
                        pid = "0"
                    path = g_split_list[1].strip()
                    path = path.replace('"', '')
                    if not path:
                        path = 'null'
                    wdl.add(hostname=hostname, pid=pid, path=path)

        return _status('UPDATED')
    else:
        return 'Content-Type not supported!'


@app.route('/info2', methods=['GET'])
def info2():
    database = dict()
    for key in r.scan_iter():
        # print(key)
        database[key.decode()] = pickle.loads(r.get(key))

    return json.dumps(database)


def _gen_info():
    database = dict()
    for key in r.scan_iter():
        # print(key)
        database[key.decode()] = pickle.loads(r.get(key))

    copy_database = dict(sorted(database.items(), key=lambda i: i[0]))
    name_title = 'name'
    cpu_system_title = 'cpu[s]'
    cpu_user_title = 'cpu[u]'
    gpu_title = 'gpu'
    nowtime_title = 'last updated'
    name_len = len(name_title)
    cpu_user_len = len(cpu_system_title)
    cpu_system_len = len(cpu_system_title)
    gpu_len = len(gpu_title)
    nowtime_len = len(nowtime_title)
    for k in copy_database:
        data = copy_database.get(k)
        name = k
        if len(name) > name_len:
            name_len = len(name)

        gpu_list = data.get('gpu')
        if gpu_list:
            new_gpu_list = []
            for gpu in gpu_list:
                if len(gpu) > 60:
                    new_gpu_list.append(gpu[0:60] + '...')
                else:
                    new_gpu_list.append(gpu)
            for gpu in new_gpu_list:
                if len(gpu) > gpu_len:
                    gpu_len = len(gpu)
            data['gpu'] = new_gpu_list

        cpu_dict = dict(data.get('cpu'))
        cpu_user = '{:.1f}%'.format(cpu_dict.get('user') * 100)
        cpu_system = '{:.1f}%'.format(cpu_dict.get('system') * 100)
        if len(cpu_user) > cpu_user_len:
            cpu_user_len = len(cpu_user)
        if len(cpu_system) > cpu_system_len:
            cpu_system_len = len(cpu_system)

        nowtime = data.get('other').get('nowtime')
        nowtime = nowtime.split(' ')[1]
        if nowtime:
            if len(nowtime) > nowtime_len:
                nowtime_len = len(nowtime)

    # name
    lines_cut = '+'
    for _ in range(name_len):
        lines_cut += '-'
    # cpu system
    lines_cut += '+'
    for _ in range(cpu_system_len):
        lines_cut += '-'
    # cpu user
    lines_cut += '+'
    for _ in range(cpu_user_len):
        lines_cut += '-'
    # gpu
    lines_cut += '+'
    for _ in range(gpu_len):
        lines_cut += '-'
    # latst update
    lines_cut += '+'
    for _ in range(nowtime_len):
        lines_cut += '-'
    lines_cut += '+'
    lines_cut += '\n'

    lines = str()
    for k in copy_database.keys():
        data = copy_database.get(k)
        gpu_list = data.get('gpu')
        if not gpu_list:
            continue
        new_gpu_list = list()
        for gl in gpu_list:
            if len(gl):
                new_gpu_list.append(gl)

        add = False
        for i, g in enumerate(new_gpu_list):
            if i == 0:
                name = k
            else:
                name = ''
            for _ in range(int((name_len - len(name)) / 2)):
                name = ' {} '.format(name)
            if len(name) != name_len:
                name = ' ' + name

            if i == 0:
                cpu_system = '{:.1f}%'.format(
                    data.get('cpu').get('system') * 100)
            else:
                cpu_system = ''
            for _ in range(int((cpu_system_len - len(cpu_system)) / 2)):
                cpu_system = ' {} '.format(cpu_system)
            if len(cpu_system) != cpu_system_len:
                cpu_system = ' ' + cpu_system

            if i == 0:
                cpu_user = '{:.1f}%'.format(data.get('cpu').get('user') * 100)
            else:
                cpu_user = ''
            for _ in range(int((cpu_user_len - len(cpu_user)) / 2)):
                cpu_user = ' {} '.format(cpu_user)
            if len(cpu_user) != cpu_user_len:
                cpu_user = ' ' + cpu_user

            gpu = g
            for _ in range(int((gpu_len - len(gpu)) / 2)):
                gpu = ' {} '.format(gpu)
            if len(gpu) != gpu_len:
                gpu = ' ' + gpu

            if i == 0:
                nowtime = data.get('other').get('nowtime')
                nowtime = nowtime.split(' ')[1]
            else:
                nowtime = ''
            for _ in range(int((nowtime_len - len(nowtime)) / 2)):
                nowtime = ' {} '.format(nowtime)
            if len(nowtime) != nowtime_len:
                nowtime = ' ' + nowtime

            l = '|{}|{}|{}|{}|{}|\n'.format(
                name, cpu_system, cpu_user, gpu, nowtime)
            lines += l
            add = True
        if add == True:
            lines += lines_cut

    for _ in range(int((name_len - len(name_title)) / 2)):
        name_title = ' {} '.format(name_title)
    if len(name_title) != name_len:
        name_title = ' ' + name_title

    for _ in range(int((cpu_system_len - len(cpu_system_title)) / 2)):
        cpu_system_title = ' {} '.format(cpu_system_title)
    if len(cpu_system_title) != cpu_system_len:
        cpu_system_title = ' ' + cpu_system_title

    for _ in range(int((cpu_user_len - len(cpu_user_title)) / 2)):
        cpu_user_title = ' {} '.format(cpu_user_title)
    if len(cpu_user_title) != cpu_user_len:
        cpu_user_title = ' ' + cpu_user_title

    for _ in range(int((gpu_len - len(gpu_title)) / 2)):
        gpu_title = ' {} '.format(gpu_title)
    if len(gpu_title) != gpu_len:
        gpu_title = ' ' + gpu_title

    for _ in range(int((nowtime_len - len(nowtime_title)) / 2)):
        nowtime_title = ' {} '.format(nowtime_title)
    if len(nowtime_title) != nowtime_len:
        nowtime_title = ' ' + nowtime_title

    lines_title = '|{}|{}|{}|{}|{}|\n'.format(
        name_title, cpu_system_title, cpu_user_title, gpu_title, nowtime_title)

    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    info_str = '>>> {} [AI Sec Lab]\n'.format(time_str)
    lines = info_str + lines_cut + lines_title + lines_cut + lines

    return lines


@app.route('/info', methods=['GET'])
def info():
    # if len(DATABASE) <= 0:
    #     return _status('NO DATA YET!')
    info = _gen_info()
    return info


@app.route('/searchpid/<hostname>/<pid>')
def searchpid(hostname, pid):
    # return (hostname + ':' + pid)
    with WatchdogLog() as wgl:
        result = wgl.searchpid(hostname=hostname, pid=pid)
        if result:
            result_str = '\n'.join(result)
            return _status(result_str)
    return _status('null')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7070, debug=False)
