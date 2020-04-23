from app import app
from datetime import datetime
from pprint import pprint
import os, time
import requests
import json
import sys
import subprocess
import os
import random
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from datetime import datetime
from flask import Flask
from flask import request


# PASTE_BOT'S_ACCESS_TOKEN
bearer = ""

# Paste webhookUrl
webhookUrl = ""

# Paste below email addresses of Webex users who will receive a daily report with an aggregated statistic from the bot
reportPeopleEmailList = ["email1@webex.com", "email2@webex.com", "email3@webex.com"]


# Set your custom report time (24-hour format)
reportTime = '20:00'

headers = {
    "Accept": "application/json",
    "Content-Type": "application/json; charset=utf-8",
    "Authorization": "Bearer " + bearer
}

#### Functions

def createWebhook(bearer, webhookUrl):
    hook = True
    botWebhooks = send_webex_get("https://api.ciscospark.com/v1/webhooks")["items"]
    for webhook in botWebhooks:
        if webhook["targetUrl"] == webhookUrl:
            hook = False
    if hook:
        dataWebhook = {
        "name": "Report collab bot Webhook",
        "resource": "messages",
        "event": "created",
        "targetUrl": webhookUrl
        }
        send_webex_post("https://api.ciscospark.com/v1/webhooks/", dataWebhook)
    print("Webhook status: done")

def send_webex_get(url, payload=None,js=True):

    if payload == None:
        request = requests.get(url, headers=headers)
    else:
        request = requests.get(url, headers=headers, params=payload)
    if js == True:
        if request.status_code == 200:
            try:
                r = request.json()
            except json.decoder.JSONDecodeError:
                print("Error JSONDecodeError")
                return("Error JSONDecodeError")
            return r
        else:
            print (request)
            return ("Error " + str(request.status_code))
    return request


def send_webex_post(url, data):

    request = requests.post(url, json.dumps(data), headers=headers).json()
    return request


def help_me():

    return "Of course! I can help. Below are the commands I understand: <br/>" \
            "`help` - I'll show you what I can do. <br/>" \
            "`+` - played sports <br/>" \
            "`-` - did not play sports <br/>" \
           "Switch off Markdown Formats (second item in the panel below) if you can send `+` or `-`"


def greetingsPlus():
    with open("sentence_done.txt", "r+") as f:
        return random.choice(f.read().split('\n'))

def greetingsMinus():
    with open("sentence_unfinished.txt", "r+") as f:
        return random.choice(f.read().split('\n'))

def appendList(email, plusL=True):
    if plusL:
        with open("listPlus.txt", "a") as f:
            f.write(email + '\n')
    else:
        with open("listMinus.txt", "a") as f:
            f.write(email + '\n')

def getlist(pList=True):
    if pList:
        with open("listPlus.txt", "r+") as f:
            return f.read().split('\n')
    else:
        with open("listMinus.txt", "r+") as f:
            return f.read().split('\n')

def clearLists():
    open('listPlus.txt', 'w').close()
    open('listMinus.txt', 'w').close()

def lastReportDate(get=True, tdate=False):
    if get:
        with open("lastReportDate.txt", "r") as f:
            return f.read()
    else:
        with open("lastReportDate.txt", "w") as f:
            if tdate:
                f.write(tdate)
                return True
            f.write(datetime.now().strftime('%d/%m/%Y'))


@app.route('/', methods=['GET', 'POST'])
def webex_webhook():
    if request.method == 'POST':
        webhook = request.get_json(silent=True)
        pprint(webhook['data']['personEmail'])
        msg = None
        if "@webex.bot" not in webhook['data']['personEmail']:
            result = send_webex_get('https://api.ciscospark.com/v1/messages/{0}'.format(webhook['data']['id']))
            in_message = result.get('text', '').lower()
            print(in_message)
            #in_message = in_message.replace(bot_name.lower() + " ", '')
            answerList = getlist() + getlist(pList=False)
            if in_message.startswith('help'):
                msg = help_me()
            # You can edit symbol `+` if the user writes this
            # symbol at the appropriate time interval, it will be added to the
            # list of those who completed the task
            elif in_message.startswith('+'):
                if webhook['data']['personEmail'] not in answerList:
                    msg = greetingsPlus()
                    appendList(webhook['data']['personEmail'])
                else:
                    # Bot response if user answer has already been recorded today
                    msg = "Your answer has already been recorded today"
            # You can edit symbol `-` if the user writes this
            # symbol at the appropriate time interval, it will be added to the
            # list of those who NOT completed the task
            elif in_message.startswith('-'):
                if webhook['data']['personEmail'] not in answerList:
                    msg = greetingsMinus()
                    appendList(webhook['data']['personEmail'], plusL=False)
                else:
                    # Bot response if user answer has already been recorded today
                    msg = "Your answer has already been recorded today"
            else:
                # Bot response if users message will not be recognized
                msg = "Sorry, but I did not understand your request. Type `help` to see what I can do <br/>" \
                      "Switch off Markdown Formats (second item in the panel below) if you can send `+` or `-`"
            if msg != None:
                send_webex_post("https://api.ciscospark.com/v1/messages",
                                {"roomId": webhook['data']['roomId'], "markdown": msg})
        return "true"
    elif request.method == 'GET':
        message = "<center><img src=\"http://bit.ly/SparkBot-512x512\" alt=\"Webex Bot\" style=\"width:256; height:256;\"</center>" \
                  "<center><h2><b>Congratulations! Your <i style=\"color:#ff8000;\"></i> bot is up and running.</b></h2></center>" \
                  "<center><b><i>Please don't forget to create Webhooks to start receiving events from Webex Teams!</i></b></center>"
        return message

def sendStatistic():
    plusList = getlist()
    minusList = getlist(pList=False)
    if plusList[-1] == '':
        del plusList[-1]
    if minusList[-1] == '':
        del minusList[-1]
    if ((datetime.now().strftime('%H:%M') >= reportTime) and (lastReportDate() < str(datetime.now().strftime('%d/%m/%Y')))):
        lastReportDate(get=False, tdate=datetime.now().strftime('%d/%m/%Y'))
        print("lastReportDate in if[", lastReportDate(), "]")
        # Create a list of Name and Surname
        plusNameSurnameString = ""
        minusNameSurnameString = ""
        for email in plusList:
            resp = send_webex_get('https://api.ciscospark.com/v1/people?email=' + email)
            if str(resp).startswith('Error'):
                plusNameSurnameString += (resp + '\n\n')
            else:
                plusNameSurnameString += (resp["items"][0]["displayName"] + '\n\n')
        print("plusNameSurnameString", plusNameSurnameString)
        for email in minusList:
            resp = send_webex_get('https://api.ciscospark.com/v1/people?email=' + email)
            if str(resp).startswith('Error'):
                plusNameSurnameString += (resp + '\n\n')
            else:
                minusNameSurnameString += (resp["items"][0]["displayName"] + '\n\n')
        print("minusNameSurnameString", minusNameSurnameString)
        # Create daily report message
        dailyReportText = "Date {} \n # Number of pluses - {} \n {} # Number of minuses - {} \n {}".format(str(datetime.now().strftime('%d/%m/%Y')), len(plusList), plusNameSurnameString, len(minusList), minusNameSurnameString)
        for email in reportPeopleEmailList:
            body = {
                "toPersonEmail": email,
                # Markdown text
                "markdown": dailyReportText,
                # This text would be displayed by Webex Teams clients that do not support markdown.
                "text": "This text would be displayed by Webex Teams clients that do not support markdown."
            }
            send_webex_post('https://api.ciscospark.com/v1/messages', body)
        #
        clearLists()


clearLists()
lastReportDate(get=False, tdate='17/04/2020')
createWebhook(bearer, webhookUrl)

sched = BackgroundScheduler(daemon=True)
sched.add_job(sendStatistic, 'interval', minutes=60)
sched.start()
