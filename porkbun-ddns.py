import os
import json
import sys
import requests
import socket
import argparse

parser = argparse.ArgumentParser(
                    prog='Improved Porkbun DDNS Python Script',
                    description='Fork of Porkbun\'s deprecated Python DDNS Client which only re-creates the DNS record if your IP address has actually changed.'                    
		)
parser.add_argument('root_domain', help="root domain whose DNS record you would like to update")
parser.add_argument("-s", "--subdomain", required=False, help="you can optionally specify a subdomain to be updated")
parser.add_argument("-w", "--wildcard", required=False, action='store_true', help="flag to create/update a corresponding wildcard DNS record on the specified domain. The same as specifying --subdomain \"*\"")
parser.add_argument("-i", "--ip", required=False, help= "manually specify your IP address. Otherwise, your IP address will automatically be fetched from Porkbun.")
parser.add_argument("-c", "--cache-ip", required=False, action='store_true', help="only update any DNS records if your IP address has changed")

arguments = parser.parse_args()

scriptPath = os.path.dirname(os.path.abspath(__file__))
cachedIpFilePath = os.path.join(scriptPath, "ip.txt")


def getRecords(domain): #grab all the records so we know which ones to delete to make room for our record. Also checks to make sure we've got the right domain
	allRecords=json.loads(requests.post(apiConfig["endpoint"] + '/dns/retrieve/' + domain, data = json.dumps(apiConfig)).text)
	if allRecords["status"]=="ERROR":
		print('Error getting domain. Check to make sure you specified the correct domain, and that API access has been switched on for this domain.');
		sys.exit();
	return(allRecords)

	
def getMyIP():
	ping = json.loads(requests.post(apiConfig["endpoint"] + '/ping/', data = json.dumps(apiConfig)).text)
	try:
		ip = ping["yourIp"]
		cacheMyIP(ip)
		return ip
	except KeyError:
		raise Exception(str(ping))


def cacheMyIP(myIP):
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
	for i in getRecords(rootDomain)["records"]:
		if i["name"]==rootDomain and (i["type"] == 'A' or i["type"] == 'ALIAS' or i["type"] == 'CNAME'):
			print("Deleting existing " + i["type"] + " Record")
			requests.post(apiConfig["endpoint"] + '/dns/delete/' + rootDomain + '/' + i["id"], data = json.dumps(apiConfig))


def createRecord(rootDomain, subDomain, myIP):
	createObj=apiConfig.copy()
	createObj.update({'name': subDomain, 'type': 'A', 'content': myIP, 'ttl': 300})
	print("Creating record: " + rootDomain + " with answer of " + myIP)
	create = json.loads(requests.post(apiConfig["endpoint"] + '/dns/create/'+ rootDomain, data = json.dumps(createObj)).text)
	return(create)


apiConfig = json.load(open(os.path.join(scriptPath, "config.json")))
myIP = arguments.ip if arguments.ip else getMyIP()
rootDomain = arguments.root_domain
subdomain = "*" if arguments.wildcard else arguments.subdomain

if (not arguments.cache_ip or hasMyIpChanged(myIP)):
	deleteRecords(rootDomain)
	record = createRecord(rootDomain, subdomain, myIP)
	print(str(record))
else:
	print(f"Your IP address hasn't changed, it's still {myIP}. No need to update its DNS records.")