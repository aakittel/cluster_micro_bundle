'''
Create a micro bundle
Hopefully can be used to gather proactive bundles 

TODO
read encrypted creds
- hashlib
- Salting
- bcrypt
- scrypt
- https://pagorun.medium.com/password-encryption-in-python-securing-your-data-9e0045e039e1

'''
import argparse
import getpass
import threading
import time
from app_data import ApiCall, Nodes, Bundle
def get_args():
#==================================
# Provide one argument. The cluster AIQ ID
    cmd_args = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    cmd_args.add_argument('-su', '--storage_admin', help='Specify storage cluster admin user')
    cmd_args.add_argument('-sp', '--storage_passwd', help='Specify storage cluster admin user password')
    required_named = cmd_args.add_argument_group('required named arguments')
    required_named.add_argument('-m', '--mvip', help='Specify storage cluster MVIP')
    return cmd_args.parse_args()

if __name__ == "__main__":
    args = get_args()
    ac = ApiCall()
    if args.storage_admin is None:
        ac.storage_admin = input('Enter the storage admin userid: ')
    else:
        ac.storage_admin = args.storage_admin
    if args.storage_passwd is None:
        ac.storage_passwd = getpass.getpass(prompt=f'Storage {ac.storage_admin} password: ')
    else:
        ac.storage_passwd = args.storage_passwd

    #==================================
    # Use ListActiveNodes to get the node list
    ac.mvip = args.mvip
    Nodes.cluster_get_nodes(ac)

    # 2 for loops is redundant. However, makes the ouput flow look much better
    for node in ac.nodes:
        delete = Bundle.delete_existing_bundle(ac, node['mip'])
        print(f'\t{delete}')
    for node in ac.nodes:
        bundle = threading.Thread(target=Bundle.make_bundle, args=(ac, node['mip'], node['name']))
        bundle.start()

    time.sleep(5)
    print('\nWaiting for support bundles to complete', end=" ")
    while len(ac.bundles) != len(ac.nodes):
        print('.', end=" ")
        time.sleep(5)
    print('Collection complete')

    for bundle in ac.bundles:
        print(f'\t{bundle}')

    for bundle in ac.bundles:
        ac.working_node = bundle.split('/')[-1].split('.tar')[0]
        if 'Concurrent bundle creation is not allowed' not in bundle:
            Bundle.download(ac, bundle)
    
    # tar up the node bundles into one cluster bundle
    Bundle.make_tar(ac)