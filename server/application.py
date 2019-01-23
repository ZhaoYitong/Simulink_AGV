from flask import Flask, session, render_template, redirect, request
from flask_sqlalchemy import SQLAlchemy
from manage import Term, Task, INPORT, OUTPORT, SHIPCYCLE, YARDCYCLE
from facilities import QC, ARMG, AGV
from traffic import TrafficDispatcher, AGVHandler
import models
import settings
import subprocess
import json
import sim_params


def start_traffic_server(address):
    traffic_dispatcher = TrafficDispatcher(address, AGVHandler)
    traffic_dispatcher.serve_forever()


app = Flask(__name__)
app.config.from_object(settings.DBConfiguration)
app.secret_key = b'\x02v\xe6\xa5\xfbC\x0b)\xe8\x1am$a\xafm5'

db = SQLAlchemy(app)


@app.route('/')
def index():
    if 'username' in session:
        username = session['username']
        return render_template('index.html', name=username)
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['username'] = request.form['username']
        return redirect('/')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/')


@app.route('/add_container', methods=['POST'])
def add_container():
    username = None
    if 'username' in session:
        username = session['username']
    flag = int(request.form['flag'])
    bay = int(request.form['bay']) if request.form['bay'] else None
    cycle_bay = int(request.form['cycle_bay']) if request.form['cycle_bay'] else None
    yard = int(request.form['yard']) if request.form['yard'] else None
    cycle_yard = int(request.form['cycle_yard']) if request.form['cycle_yard'] else None
    container = models.Container(user=username, flag=flag, bay=bay, cycle_bay=cycle_bay,
                                 yard=yard, cycle_yard=cycle_yard)
    db.session.add(container)
    db.session.commit()
    return '{"status": "ok", "container_id": "%s"}' % container.id


@app.route('/add_preset', methods=['POST'])
def add_preset():
    username = None
    if 'username' in session:
        username = session['username']
    num_qc = int(request.form['num_qc'])
    num_armg = int(request.form['num_qc'])
    num_agv = int(request.form['num_qc'])
    preset = models.Preset(user=username, num_qc=num_qc, num_armg=num_armg, num_agv=num_agv)
    db.session.add(preset)
    db.session.commit()
    return '{"status": "ok", "preset_id": "%s"}' % preset.id


@app.route('/set_simdata', methods=['POST'])
def set_simdata():
    json_data = request.get_json()
    sim = models.Sim(qcs=json_data['qcs'], armgs=json_data['armgs'], agvs=json_data['agvs'], containers=json_data['containers'])
    db.session.add(sim)
    db.session.commit()
    return '{"status": "ok", "sim_id": "%s"}' % sim.id


@app.route('/get_simdata', methods=['GET'])
def get_simdata():
    sim_id = request.args.get("sim_id")
    sim = models.Sim.query.filter_by(id=sim_id).first()
    agv_ids = sim.agvs.split(',')
    position = [models.AGV.query.filter_by(id=int(agv_id)).first().position for agv_id in agv_ids]
    return '{"agv": %s, "position": %s}' % ([int(agv_id) for agv_id in agv_ids], position)


@app.route('/run_traffic', methods=['GET'])
def run_traffic():
    traffic_server_process = subprocess.Popen(["python", "traffic.py", "8086"], creationflags=subprocess.CREATE_NEW_CONSOLE)
    return '{"status": "ok", "pid": %s}' % traffic_server_process.pid


@app.route('/run_sim', methods=['GET', 'POST'])
def run_sim():
    """测试入口，本地交通控制器端口8086，不可多用户运行"""
    username = 'admin'
    if 'username' in session:
        username = session['username']
    json_data = request.get_json()
    preset = models.Preset.query.filter_by(id=json_data['preset_id']).first()

    traffic_dispatch_address = ("127.0.0.1", 8086)

    term = Term(preset.factor, traffic_dispatch_address, num_qc=preset.num_qc, num_armg=preset.num_armg, num_agv=preset.num_agv)
    for facility in json_data['facilities']:
        if facility['type'] == 'qc':
            qc = models.QC.query.filter_by(id=facility['id'], user=username).first()
            term.add_facility(QC(term.env, 'qc_%s' % qc.id, qc.position, qc.lanes.split(','), traffic_dispatch_address, term.task_manager))
        elif facility['type'] == 'armg':
            armg = models.ARMG.query.filter_by(id=facility['id'], user=username).first()
            term.add_facility(ARMG(term.env, 'armg_%s' % armg.id, armg.position, armg.lanes.split(','), traffic_dispatch_address, term.task_manager))
        elif facility['type'] == 'agv':
            agv_speed = int(sim_params.AGV_SPEED / preset.factor)
            agv = models.AGV.query.filter_by(id=facility['id'], user=username).first()
            term.add_facility(AGV(term.env, 'agv_%s' % agv.id, agv.position, traffic_dispatch_address, agv_speed, term.task_manager))

    tasks = []
    for task in json_data['tasks']:
        container = models.Container.query.filter_by(id=task['container_id'], user=username).first()
        start_facility, end_facility = None, None
        if container.flag == INPORT:
            start_facility = term.facilities['qc_%s' % task['start_facility_id']]
            end_facility = term.facilities['armg_%s' % task['end_facility_id']]
        elif container.flag == OUTPORT:
            start_facility = term.facilities['armg_%s' % task['start_facility_id']]
            end_facility = term.facilities['qc_%s' % task['end_facility_id']]
        elif container.flag == SHIPCYCLE:
            start_facility = term.facilities['qc_%s' % task['start_facility_id']]
            end_facility = term.facilities['qc_%s' % task['end_facility_id']]
        elif container.flag == YARDCYCLE:
            start_facility = term.facilities['armg_%s' % task['start_facility_id']]
            end_facility = term.facilities['armg_%s' % task['end_facility_id']]
        if start_facility and end_facility:
            tasks.append(Task(raw_id=task['container_id'], priority=task['priority'], container=container,
                              start_facility=start_facility, end_facility=end_facility, transporter=term.facilities['agv_%s' % task['transporter_id']]))
        else:
            return {"status": "error", "value": "Invalid task %s." % task}
    term.tasks = tasks
    term.env.sync()
    now = term.run()
    return '{"status": "ok", "sim_time": %s, "data": %s}' % (now, json.dumps(term.env._data))


@app.route('/test', methods=['GET', 'POST'])
def test():
    return '{"request": "%s"}' % str(request.get_json())


if __name__ == '__main__':
    app.run('0.0.0.0', 80)
