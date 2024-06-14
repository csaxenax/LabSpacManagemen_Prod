import requests
import json
from .models import UserModel
from rest_framework.response import Response
from rest_framework import status
def GetIAMInternalToken():
    username = 'sys_toolscps'
    password = 'intel@123456789012345'
    token_url =  'https://iamws-i.intel.com/api/v1/token'
    token_payload = {'scope':'Authorization'}
    token_headers = {'Content-Type':'application/json'}
    token_response = requests.request("POST", token_url, headers=token_headers, data=token_payload, auth=(username,password),verify=False).json()
    bearer_token = token_response['access_token']
    return bearer_token


def GetUserData(iamToken):
    internal_token  = GetIAMInternalToken()
    # get the user data
    try:
        user_data_url =  "https://cppo.apps1-bg-int.icloud.intel.com/api/UserAuth/Authentications"
        user_data_url_headers = {'Content-Type':'application/json','Accept':'application/json','Authorization':'Bearer '+internal_token}
        user_data_url_body = {'token':iamToken}
        user_data_response = requests.post(url = user_data_url, headers=user_data_url_headers, json =  user_data_url_body,verify=False).json()
        return user_data_response
    except Exception as e:
        return e
   



