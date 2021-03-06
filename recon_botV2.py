__author__      = "Rahul R"
__github__      = "https://github.com/rahulr311295"
import argparse
import os
import time
import sys
from termcolor import colored
from slacker import Slacker
import install_tool
import psycopg2
import requests
import re
import json
from tld import get_fld
import urllib3
from requests.exceptions import HTTPError
urllib3.disable_warnings()
# Mysql Connection
import pymysql

# reading config data from json and converting it to python object
config = json.loads(open('config.json').read())

# configuring slack token
slack_token = config['slack']['token']
slack = Slacker(slack_token)

# establishing database connection
db_host = config['database']['host']
db_username = config['database']['username']
db_password = config['database']['password']
db = pymysql.connect(host = db_host, user = db_username, passwd = db_password)

cursor = db.cursor()
# -----------------#
aquatone_path=config['aquatone_path']['path']
newpath = r'output'
if not os.path.exists(newpath):
    os.makedirs(newpath)


def banner():
	print(colored("""
  _____                      ____        _   
 |  __ \                    |  _ \      | |  
 | |__) |___  ___ ___  _ __ | |_) | ___ | |_ 
 |  _  // _ \/ __/ _ \| '_ \|  _ < / _ \| __|
 | | \ \  __/ (_| (_) | | | | |_) | (_) | |_ 
 |_|  \_\___|\___\___/|_| |_|____/ \___/ \__|
                                             v2.0""","red"))

def get_args():
    parser = argparse.ArgumentParser(
        description='Recon')
    parser.add_argument('--install',help='Install Dependencies and Tools',action='store_true',default=False)
    parser.add_argument(
        '-d', '--domain', type=str, help='Domain', required=False, default=False)
    parser.add_argument(
         '--brute', help='Start Massdns on subdomains', action="store_true", default=False)
    parser.add_argument(
         '--init',  help='Initialize BOT creating Database and stuff', action="store_true", default=False)
    parser.add_argument(
        '--monitor','-m', help='Start monitor module',action="store_true", required=False, default=False)
    parser.add_argument(
        '--zombie', help='Start Zombie Module', action='store_true', default=False)
    return parser.parse_args()
class initialze_db:
	def create_db(self):
		# initializing databases and corresponding tables
		try:
			cursor.execute("CREATE DATABASE recon")
			cursor.execute("CREATE DATABASE monitor")
			print(colored("Recon and Monitor Databases Created","green"))
			cursor.execute("USE monitor;")
			print(colored("Creating monitor Table"))
			cursor.execute("CREATE TABLE `monitor` (`id` INT(255) NOT NULL AUTO_INCREMENT PRIMARY KEY,`domain` VARCHAR(150) NOT NULL);")
			print(colored("Monitor Table Created","green"))
		except:
			print(colored("\nDatabase Already Exists, kindly check it manually","red"))

		# initializing and verifying slack configuration
		try:
			print(colored("Sending Sample message to Slack Bot"))
			slack.chat.post_message("#recon","```Hi, I am ReconBot! ```")
		except:
			print(colored("\nThere is something wrong with the Slack configuration, kindly check your Slack token in config.json file","red"))

class persistence_modules:
	def monitor(self,wildcard=True):
		cursor.execute("USE monitor;")
		cursor.execute("SELECT domain FROM monitor;")
		result=cursor.fetchall()
		for row in result:
			domain=''.join(row)
			try:
				unique_domains = set()
				domain = domain.replace('%25.', '')
				print(colored("Connecting to crt.sh database","blue"))
				conn = psycopg2.connect("dbname=certwatch user=guest host=crt.sh")
				conn.autocommit =True
				postgres_cursor=conn.cursor()
				postgres_cursor.execute("SELECT ci.NAME_VALUE NAME_VALUE FROM certificate_identity ci WHERE ci.NAME_TYPE = 'dNSName' AND reverse(lower(ci.NAME_VALUE)) LIKE reverse(lower('%{}'));".format(domain))
				for result in postgres_cursor.fetchall():
					matches = re.findall(r"\'(.+?)\'", str(result))
					for subdomain in matches:
						try:
							if get_fld("https://"+subdomain)==domain:
								unique_domains.add(subdomain.lower())
						except: pass
				print("Pulling data from DB")
				print(sorted(unique_domains))
			except:
				url = "https://crt.sh/?q=%25.{}&output=json".format(domain)
				subdomains = set()
				user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:64.0) Gecko/20100101 Firefox/64.0'
				req = requests.get(url, headers={'User-Agent': user_agent}, timeout=20, verify=False)
				if req.status_code == 200:
					try:
						parsed=json.loads(req.content)
						for subdomains in parsed:
							print(subdomains['name_value'])
							f = open("api.txt", "a")
							f.write(subdomains['name_value']+"\n")
							

					except:
						print("error")

		
	def zombie(self):
		cursor.execute("USE recon")
		cursor.execute("SHOW TABLES")
		result=cursor.fetchall()
		for records in result:
			domain_name=''.join(records)
			state="""SELECT `subdomain` from `%s` WHERE is_alive=0 """%(domain_name)
			try:
				cursor.execute(state)
				results = cursor.fetchall()
				for row in results:
					subdomain_name=''.join(row)
					try:
						response=requests.get("http://"+subdomain_name,timeout=(5, 27))
						response.raise_for_status()
						if response.status_code == 200 or response.status_code == 301 or response.status_code == 302:
							sql="""UPDATE `%s` SET `is_alive` = True WHERE `subdomain` = '%s' ;"""%(domain_name,subdomain_name)
							cursor.execute(sql)
							aquatone="""echo {} | aquatone -out {}{}""".format(subdomain_name,aquatone_path,domain_name)
							os.system(aquatone)
						else :
							pass
					except Exception as err:
						print("Cant connect to Host "+subdomain_name)
			except:
				print("Zombie Died")
				db.close()




class recon:
	def domain_todb(self):
		cursor.execute("USE recon;")
		stmt = "SHOW TABLES LIKE '{}'".format(domain)
		cursor.execute(stmt)
		result = cursor.fetchone()
		if result:
		    print("Domain table already Exists")
		    pass
		else:
			cursor.execute("USE monitor;")
			cursor.execute("INSERT INTO `monitor` (`domain`) VALUES ('"+domain+"');")
			db.commit()
			print(colored(str(domain)+" added to Monitor Table","green"))
			cursor.execute("USE recon;")
			cursor.execute("CREATE TABLE `"+domain+"` (`id` INT(255) NOT NULL AUTO_INCREMENT PRIMARY KEY,`subdomain` varchar(150) NOT NULL UNIQUE,`is_alive` BOOLEAN NOT NULL );")
			print(colored(domain+" table created on Recon","green"))
	def amass(self):
	    print("\n\n\033[1;31mRunning Amass \n\033[1;37m")
	    AmassFileName = "{}_amass.txt".format(output_base)
	    amasscmd = "amass enum -d {} -o {}".format(domain,AmassFileName)
	    print("\n\033[1;31mRunning Command: \033[1;37m{}".format(amasscmd))
	    os.system(amasscmd)
	    print("\n\033[1;31mAmass Complete\033[1;37m")
	    time.sleep(1)
	def subfinder(self):
		print("\n\n\033[1;31mRunning Subfinder \n\033[1;37m")
		SubfinderFileName="{}_subfinder.txt".format(output_base)
		subfincmd="subfinder -d {} -v -o {}".format(domain,SubfinderFileName)
		os.system(subfincmd)
		print("\n\033[1;31mSubfinder Complete\033[1;37m")
		time.sleep(1)
	def knockpy(self):
		print("\n\n\033[1;31mRunning Knock \n\033[1;37m")
		knockpyCmd = "python {} -c {}".format(os.path.join(script_path, "bin/knockpy/knockpy/knockpy.py"), domain)
		print("\n\033[1;31mRunning Command: \033[1;37m {}".format(knockpyCmd))
		os.system(knockpyCmd)
		rootdomainStrip = domain.replace(".", "_")
		knockpyFilenameInit = "{}_knock.csv".format(output_base)
		os.system("mv {}* {}".format(rootdomainStrip, knockpyFilenameInit))
		time.sleep(1)
		knockpySubs = []
		try:
			with open(knockpyFilenameInit, "rb") as f:
				reader = csv.reader(f, delimiter=",")
				for row in reader:
					knockpySubs.append(row[3])
			filenameKnocktxt = "{}.txt".format(knockpyFilenameInit)
			f1 = open(filenameKnocktxt, "w")
			for hosts in knockpySubs:
				hosts = "".join(hosts)
				f1.writelines("\n" + hosts)
				f1.close()
		except:
			print("\nKnock File Error\n")
	time.sleep(1)

	def subdomainfile(self):
		AmassFileName = "{}_amass.txt".format(output_base)
		SubfinderFileName="{}_subfinder.txt".format(output_base)
		subdomainAllFile = "{}-all.txt".format(output_base)
		massdnsFileName = "{}-massdns.txt".format(output_base)
		knockpyFileName = "{}_knock.csv.txt".format(output_base)
		f1 = open(subdomainAllFile, "w")
		f1.close()
		print("\nOpening Amass File\n")
		try:
			with open(AmassFileName) as f:
				SubHosts = f.read().splitlines()
			f.close()
			time.sleep(2)
			subdomainCounter = 0
			f1 = open(subdomainAllFile, "a")
			f1.writelines("\n\nsublist3r")
			for hosts in SubHosts:
				hosts = "".join(hosts)
				f1.writelines("\n" + hosts)
				subdomainCounter = subdomainCounter + 1
			f1.close()
			os.remove(AmassFileName)
			print("\n{} Subdomains discovered by Amass".format(subdomainCounter))
		except:
			print("\nError Opening Amass File!\n")
		print("\nOpening massdns File\n")
		try:
			with open(massdnsFileName) as f:
				SubHosts = f.read().splitlines()
			f.close()
			time.sleep(1)
			subdomainCounter = 0
			f1 = open(subdomainAllFile, "a")
			f1.writelines("\n\nmassdns")
			for hosts in SubHosts:
				hosts = hosts.split(".	")[0]
				if domain in hosts:
					hosts = "".join(hosts)
					f1.writelines("\n" + hosts)
					subdomainCounter = subdomainCounter + 1
			f1.close()
			os.remove(massdnsFileName)
			print("\n{} Subdomains discovered by massdns".format(subdomainCounter))
		except:
			print("\nError Opening massdns File!\n")
		print("\nOpening Subfinder File\n")
		try:
			with open(SubfinderFileName) as f:
				SubHosts = f.read().splitlines()
			f.close()
			time.sleep(2)
			subdomainCounter = 0
			f1 = open(subdomainAllFile, "a")
			f1.writelines("\n\nSubfinder")
			for hosts in SubHosts:
				hosts = "".join(hosts)
				f1.writelines("\n" + hosts)
				subdomainCounter = subdomainCounter + 1
			f1.close()
			os.remove(SubfinderFileName)
			print("\n{} Subdomains discovered by Subfinder".format(subdomainCounter))
		except:
			print("\nError Opening Subfinder File!\n")
		print("\nOpening Knock File\n")
		try:
			with open(knockpyFileName) as f:
				SubHosts = f.read().splitlines()
			f.close()
			time.sleep(1)
			subdomainCounter = 0
			f1 = open(subdomainAllFile, "a")
			f1.writelines("\n\nknock")
			for hosts in SubHosts:
				hosts = "".join(hosts)
				f1.writelines("\n{}".format(hosts))
				subdomainCounter = subdomainCounter + 1
			f1.close()
			knockpyFileNamecsv = "{}_knock.csv".format(output_base)
			os.remove(knockpyFileName)
			os.remove(knockpyFileNamecsv)
			print("\n{} Subdomains discovered by Knock".format(subdomainCounter))
		except:
			print("\nError Opening Knock File!\n")
		print("\nCombining Domains Lists\n")
		domainList = open(subdomainAllFile, 'r')
		uniqueDomains = set(domainList)
		domainList.close()
		subdomainUniqueFile = "{}-unique.txt".format(output_base)
		uniqueDomainsOut = open(subdomainUniqueFile, 'w')
		for domains in uniqueDomains:
			domains = domains.replace('\n', '')
			if domains.endswith(domain):
				uniqueDomainsOut.writelines("{}\n".format(domains))
		uniqueDomainsOut.close()
		time.sleep(1)
		rootdomainStrip = domain.replace(".", "_")


	def insert_domain_todb(self):
		f = open(output_base+"-unique.txt", "r")
		for x in f:
			print(x.strip())
			try:
				request = requests.get('http://'+x.strip(),timeout=(5,27))
				if request.status_code == 200 or request.status_code == 301 or request.status_code == 302:
					sql="INSERT IGNORE INTO `{}` (`subdomain`,`is_alive`) VALUES ('{}',TRUE);".format(domain,x.rstrip("\n\r"))
					cursor.execute(sql)
					aquatone_cmd="""echo {} | aquatone -out {}{}""".format(x.strip(),aquatone_path,domain)
					os.system(aquatone_cmd) 
				# Check if this works else find another way
					db.commit() 
				else:
					print(x.strip()+" is dead")
					sql="INSERT IGNORE INTO `{}` (`subdomain`,`is_alive`) VALUES ('{}',FALSE);".format(domain,x.rstrip("\n\r"))
					cursor.execute(sql)
					db.commit()
			except requests.exceptions.Timeout:
				print("Host TimedOut")
			except requests.exceptions.TooManyRedirects:
				print("Too Many Redirects")
			except requests.exceptions.RequestException as e:
				print("Oh Shit Something Went Wrong")

class post_recon:
	def massdns(self):
		print("\n\n\033[1;31mRunning massdns \n\033[1;37m")
		word_file = os.path.join(script_path, "bin/all.txt")
		massdnsCMD = "python {}  {} {} | {} -r {} -t A -o S -w {}-massdns.txt".format(os.path.join(script_path, "bin/massdns/scripts/subbrute.py"),word_file,domain,os.path.join(script_path, "bin/massdns/bin/massdns"),os.path.join(script_path, "bin/massdns/lists/resolvers.txt"),output_base)
		print("\n\033[1;31mRunning Command: \033[1;37m{}".format(massdnsCMD))
		os.system(massdnsCMD)
		print("\n\033[1;31mMasscan Complete\033[1;37m")
	time.sleep(1)

if __name__ == "__main__":
	banner()
	script_path = os.path.dirname(os.path.realpath(__file__))
	# monitor_func=persistence_modules()
	# monitor_func.zombie()
	args = get_args()
	brute=args.brute
	domain = args.domain
	initialize=args.init
	monitor=args.monitor
	zombie=args.zombie
	install=args.install
	output_base = "output/{}".format(domain)
	if brute:
		post_recon=post_recon()
		post_recon.massdns()

	if install:
		install_tool.installTools()

	if initialize:
		database_init_class=initialze_db()
		database_init_class.create_db()
	if domain:
		recon_class=recon()
		recon_class.domain_todb()
		recon_class.amass()
		recon_class.subfinder()
		recon_class.knockpy()
		recon_class.subdomainfile()
		recon_class.insert_domain_todb()
	if monitor:
		monitor_func=persistence_modules()
		monitor_func.monitor()
	if zombie:
		monitor_func=persistence_modules()
		monitor_func.zombie()
