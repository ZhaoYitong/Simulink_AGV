from configparser import ConfigParser
import os
import sys
import csv
import json
import time
import requests
import subprocess

DIR = sys.path[0]

conf = ConfigParser()
conf.read("client_config.conf")

server_address = conf.get("server", "server_address")

path_csv = sys.argv[1]
csv_reader = csv.reader(open(path_csv, encoding='utf-8'))
raw_data = []
for row in csv_reader:
    raw_data.append(row)
json_package = {"preset_id": 0, "facilities": [], "tasks": []}
for i, line in enumerate(raw_data):
    if "预设编号" in line[0]:
        json_package["preset_id"] = int(line[1])
    elif "作业设备" in line[0]:
        json_package["facilities"].append({"type": line[1], "id": int(line[2])})
    elif "任务" in line[0]:
        json_package["tasks"].append({"container_id": int(line[1]), "priority": int(line[3]),
                                      "start_facility_id": int(line[5]), "end_facility_id": int(line[7]),
                                      "transporter_id": int(line[8])})
package_dir = DIR + '/temp/package_%s.json' % int(time.time())
with open(package_dir, 'w') as wh:
    json.dump(json_package, wh)

init_data = {"qcs": ','.join([str(facility['id']) for facility in json_package['facilities'] if facility['type'] == 'qc']),
             "armgs": ','.join([str(facility['id']) for facility in json_package['facilities'] if facility['type'] == 'armg']),
             "agvs": ','.join([str(facility['id']) for facility in json_package['facilities'] if facility['type'] == 'agv']),
             "containers": ','.join([str(task["container_id"]) for task in json_package['tasks']])}


response = requests.post(url=server_address + "/set_simdata", headers={'Content-Type': 'application/json'}, data=json.dumps(init_data))
if not response.ok:
    raise RuntimeError("Server Error %s " % response)
sim_id = int(response.json()["sim_id"])

requests.get(url=server_address + "/run_traffic")

data_dir = DIR + r'/data/sim%s.json' % sim_id
unity_process = subprocess.Popen([DIR + r'\build\3d.exe', str(sim_id), package_dir, data_dir])
