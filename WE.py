import time
import json
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import base64
from typing import Dict, List
from datetime import datetime, timezone
from dataclasses import dataclass

class UserInfo:
	def __init__(self, Data):
		self.data = Data
	@property
	def token(self):
		return self.data['body']['utoken']
	@property
	def csrf_token(self):
		return self.data['body']['token']
	@property
	def subscriber_id(self):
		return self.data['body']['subscriber']['subscriberId']

@dataclass
class FreeUnitBeanDetail:
	initialAmount: float
	currentAmount: float
	measureUnit: str
	effectiveTime: int
	expireTime: int
	expireTimeCz: int
	originType: str
	offeringName: str
	isGroup: bool
	serviceNumber: str
	itemCode: str
	remainingDaysForRenewal: int

	def __post_init__(self):
		self.effectiveTime_dt = datetime.fromtimestamp(self.effectiveTime / 1000, tz=timezone.utc).strftime('%Y-%m-%d %I:%M:%S %p')
		self.expireTime_dt = datetime.fromtimestamp(self.expireTime / 1000, tz=timezone.utc).strftime('%Y-%m-%d %I:%M:%S %p')

@dataclass
class Quota:
	tabId: str
	freeUnitType: str
	freeUnitTypeName: str
	tabName: str
	measureUnit: str
	offerName: str
	total: float
	used: float
	remain: float
	actualRemain: float
	effectiveTime: int
	expireTime: int
	groupOrder: str
	iconImage: str
	freeUnitTypeId: str
	originUnit: str
	freeUnitBeanDetailList: List[FreeUnitBeanDetail]

	def __post_init__(self):
		self.effectiveTime_dt = datetime.fromtimestamp(self.effectiveTime / 1000, tz=timezone.utc).strftime('%Y-%m-%d %I:%M:%S %p')
		self.expireTime_dt = datetime.fromtimestamp(self.expireTime / 1000, tz=timezone.utc).strftime('%Y-%m-%d %I:%M:%S %p')
		self.freeUnitBeanDetailList = [FreeUnitBeanDetail(**detail) for detail in self.freeUnitBeanDetailList]

def setupRequests():
	session = requests.Session()
	retry = Retry(connect=3, backoff_factor=0.5)
	adapter = HTTPAdapter(max_retries=retry)
	session.mount('http://', adapter)
	session.mount('https://', adapter)
	return session

class WE:
	def __init__(self, number, password):
		self.QuotaData = []
		self.number = number.lstrip("0") if number.startswith("0") else number
		self.password = password
		self.url = 'https://my.te.eg/echannel/service/besapp/base/rest/busiservice'
		self.headers = {'Content-Type': 'application/json', 'channelId': '702', 'isSelfcare': 'true'}
		self.loginToken()

	def loginToken(self):
		self.session = setupRequests()
		json_data = {
			"acctId":f"FBB{self.number}",
			"password": self.password,
			"appLocale":"en-US",
			"isSelfcare":"Y",
			"isMobile":"N",
			"recaptchaToken":""
		}

		LoginJson = self.session.post(f'{self.url}/v1/auth/userAuthenticate', json=json_data, headers=self.headers).json()

		if LoginJson['header']['retCode'] != '0':
			error_no = LoginJson['header']['errorNo']
			if error_no == '60301023110815001':
				raise Exception('Service number or password is incorrect')
			elif error_no == '60301023110815002':
				raise Exception('You have reached the maximum number of incorrect login attempts. Please try again after 15 minutes.')
			else:
				raise Exception('unknown error has happened')

		self.userInfo = UserInfo(LoginJson)
	
	def __getQuota(self):
		json_data = {
			"subscriberId": self.userInfo.subscriber_id
		}

		self.headers.update({'csrftoken': self.userInfo.csrf_token})

		QuotaJson = self.session.post(f'{self.url}/cz/cbs/bb/queryFreeUnit', headers=self.headers, json=json_data).json()
		return QuotaJson
	
	@staticmethod
	def __getRatio(QuotaData):
		remainingDays = QuotaData["remainingDaysForRenewal"]
		remainingAmount = QuotaData["freeAmount"]
		return "{:.2f}".format(remainingAmount / remainingDays)

	def FullQuotaInfo(self):
		self.QuotaData = self.__getQuota()
		data = self.QuotaData['body'][0]
		return Quota(**data)