''' Code to make api calls
'''
import json
import os
import requests
import tarfile
import urllib3
from datetime import datetime
from requests.auth import HTTPBasicAuth 

class ApiCall():
    def __init__(self):
        self.header = {
        'Content-Type': 'application/json',
        'Authorization': 'Basic YWRtaW46YWRtaW4='
        }
        self.state_url = 'https://activeiq.solidfire.com/state/cluster'
        self.bundles = []
        self.downloads = {}
        self.mvip = ""
        self.nodes = []
        self.working_node = ""
        self.storage_admin = ""
        self.storage_passwd = ""

    def check_json(self, text):
        try:
            json_return = json.loads(text)
            return json_return
        except ValueError as error:
            print(f'An error occured: {error}')
            
    def send_get(self, url, header, payload):
        # disable ssl warnings so the log doesn't fill up
        urllib3.disable_warnings()
        print(f'api call: {url}')
        try:
            response = requests.get(url, headers=header, data=payload, verify=False, timeout=30)
            if response.status_code == 200:
                return response
            else:
                print(f'{url}\n\t{response.status_code}: {response.content}\n')
        except requests.exceptions.RequestException as exception:
            print(f'{url}\n\t{exception}\n')

    def send_post(self, url, payload):
        urllib3.disable_warnings()
        print(f'api call: {url}: {payload}')
        try:
            response = requests.post(url, headers=self.header, data=payload, verify=False, auth=HTTPBasicAuth(self.storage_admin, self.storage_passwd))#, timeout=30)
            if response.status_code == 200:
                return response
            else:
                print(f'{url}\n\t{response.status_code}: {response.content}\n')
        except requests.exceptions.RequestException as exception:
            print(exception)

class Nodes():
    def aiq_get_nodes(ac, cluster_id):
        url = f'{ac.state_url}/{cluster_id}/ListActiveNodes'
        response = ac.send_get(url, ac.aiq_header, None)
        json_return = ac.check_json(response.text)
        ac.nodes = json_return['nodes']
        return json_return['nodes']

    def cluster_get_nodes(ac):
        url = f'https://{ac.mvip}/json-rpc/12.0?method=ListActiveNodes'
        response = ac.send_get(url, ac.header, None)
        json_return = ac.check_json(response.text)
        ac.nodes = json_return['result']['nodes']
        return json_return['result']['nodes']

class Bundle():
    def delete_existing_bundle(ac, mip):
        payload = json.dumps({"method": "DeleteAllSupportBundles","params": {},"id": 1})
        url = f'https://{mip}:442/json-rpc/12.0'
        response = ac.send_post(url, payload)
        json_return = ac.check_json(response.text)
        return json_return['result']['details']['output']

    def make_bundle(ac, mip, node_name):
        url = f'https://{mip}:442/json-rpc/12.0'
        payload = json.dumps({
            "method": "CreateSupportBundle",
            "params": {
                "bundleName": node_name,
                "extraArgs": "--micro --compress gz"
            },
            "id": 1
        })
        response = ac.send_post(url, payload)
        json_return = ac.check_json(response.text)
        if 'error' in json_return:
            ac.bundles.append(json_return['error']['message'])
        else:
            ac.bundles.append(json_return['result']['details']['url'][0])

    def download(ac, url):
        local_filename = url.split('/')[-1]
        print(f'Downloading {url}')
        with requests.get(url, stream=True, verify=False) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192): 
                    f.write(chunk)
        ac.downloads[ac.working_node] = {}
        ac.downloads[ac.working_node]['filename'] = local_filename
        ac.downloads[ac.working_node]['size MB'] = str((os.stat(local_filename).st_size) / 1048576).split('.')[0]
        print(f'\tDownload complete: {ac.downloads[ac.working_node]}')
        
    def make_tar(ac):
        date_time = datetime.now()
        time_stamp = date_time.strftime("%d-%b-%Y-%H.%M.%S")
        tar_file = f'{ac.mvip}-{time_stamp}.tar.gz'
        print(f'Creating tar bundle {tar_file}')
        try:
            cluster_bundle = tarfile.open(tar_file, "w:gz")
            for download in ac.downloads:
                print(f'\tAdding {ac.downloads[download]["filename"]}\t{ac.downloads[download]["size MB"]}MB')
                cluster_bundle.add(ac.downloads[download]["filename"])
            cluster_bundle.close()
        except:
            print("Failed to create tar bundle.")
        print(f'Completed: {tar_file}')
