import os
import json
import sys
from typing import Any, Dict, List
import requests
import argparse
import time


parser = argparse.ArgumentParser (
    prog='Improved Porkbun DDNS Python Script',
    description='Working fork of Porkbun\'s deprecated Python DDNS Client which only re-creates the DNS record if your IP address has actually changed'                    
)
parser.add_argument(
    'root_domain', help="root domain whose DNS record you would like to update"
)
parser.add_argument(
    "-s", "--subdomain", required=False, help="you can optionally specify a subdomain to be updated"
)
parser.add_argument(
    "-w", "--wildcard", required=False, action='store_true', 
    help="flag to create/update a corresponding wildcard DNS record on the specified domain. The same as specifying --subdomain \"*\""
)
parser.add_argument(
    "-i", "--ip", required=False, type=str,
    help= "manually specify your IP address. Otherwise, your IP address will automatically be fetched from Porkbun."
)
parser.add_argument(
    "-c", "--cache-ip", required=False, action='store_true', 
    help="only update any DNS records if your IP address has changed"
)

arguments = parser.parse_args()

scriptPath = os.path.dirname(os.path.abspath(__file__))
cachedIpFilePath = os.path.join(scriptPath, "ip.txt")


def getRecords(domain): 
    """
    grab all the records so we know which ones to delete to make room for our record. 
    Also checks to make sure we've got the right domain
    """
    response = requests.post(apiConfig["endpoint"] + '/dns/retrieve/' + domain, data=json.dumps(apiConfig))
    response.raise_for_status()
    allRecords = response.json()
    if allRecords["status"] == "ERROR":
        print('Error getting domain. Check to make sure you specified the correct domain, and that API access has been switched on for this domain.')
        sys.exit()
    return allRecords



def getMyIP() -> str:
    response = requests.post(apiConfig["endpoint"] + '/ping/', data=json.dumps(apiConfig))
    response.raise_for_status()
    ping = response.json()
    return ping["yourIp"]



def cacheMyIP(myIP) -> None:
    file = open(cachedIpFilePath, "w")
    file.write(myIP)
    file.close


def hasMyIpChanged(myIP) -> bool:
    try:
        file = open(cachedIpFilePath, "r")
        previousIp = file.read()
        file.close()
        return myIP != previousIp
    except FileNotFoundError:
        return True


def deleteRecords(rootDomain):
    for record in getRecords(rootDomain)["records"]:
        if rootDomain in record["name"] and (record["type"] == 'A' or record["type"] == 'ALIAS' or record["type"] == 'CNAME'):
            print("Deleting existing " + record["type"] + " Record for " + record["name"])
            requests.post(apiConfig["endpoint"] + '/dns/delete/' + rootDomain + '/' + record["id"], data = json.dumps(apiConfig))


def createRecord(rootDomain, subDomain, myIP):
    createObj=apiConfig.copy()
    createObj.update({'name': subDomain, 'type': 'A', 'content': myIP, 'ttl': 300})
    print("Creating record: " + ((subDomain + ".") if subDomain else "") + rootDomain + " with answer of " + myIP)
    response = requests.post(apiConfig["endpoint"] + '/dns/create/'+ rootDomain, data = json.dumps(createObj))
    response.raise_for_status()
    create = response.json()
    return(create)

 
def run_function_until_it_succeeds(
        function_to_run, 
        parameters: List[Any] = [], 
        max_number_of_repeats: int = sys.maxsize, 
        time_between_repeats: float = 3.0
    ) -> Any:
    """
    Runs a function once and re-runs it if it throws an error.
    This repeats until the total number of repeats reaches the number_of_repeats parameter,
    at which point the script's execution is halted.
    @param function_to_run: The function whose execution should be re-tried until it succeeds
    @param parameters: The parameters this function takes
    @param number_of_repeats: How often function_to_run will be re-run after raising an error 
                              before this entire script's execution is halted
    @param time_between_repeats: How long to wait between re-runs in seconds
    @returns whatever function_to_run returns
    """
    for attempt in range(max_number_of_repeats):
        try:
            return function_to_run(*parameters)
        except Exception as e:
            print(f"Attempt {attempt + 1} to run {function_to_run.__name__} failed: {e}")
            time.sleep(time_between_repeats)
    print(f"Failed to run {function_to_run.__name__} after {max_number_of_repeats+1} attempts. Exiting.")
    sys.exit()
     

if __name__ == "__main__":
    apiConfig: Dict[str, str] = json.load(open(os.path.join(scriptPath, "config.json")))
    myIP: str = arguments.ip if arguments.ip else run_function_until_it_succeeds(getMyIP, max_number_of_repeats=3, time_between_repeats=3.0)
    rootDomain = arguments.root_domain
    subdomain = "*" if arguments.wildcard else arguments.subdomain

    if (arguments.cache_ip and not hasMyIpChanged(myIP)):
        print(f"Your IP address hasn't changed, it's still {myIP}. No need to update its DNS records.")
    else:
        run_function_until_it_succeeds(deleteRecords, [rootDomain], 3, 3.0)
        record = run_function_until_it_succeeds(createRecord, [rootDomain, subdomain, myIP], 3, 3.0)
        if record["status"] == "SUCCESS":
            cacheMyIP(myIP)
        print(str(record))
