from slackclient import SlackClient
import os, time, re, datetime, config
from peewee import *
from operator import itemgetter

slack_token = config.API_TOKEN
sc = SlackClient(slack_token)

db = SqliteDatabase('scorebot.db')

class Channel(Model):
	uid = CharField(primary_key=True)
	class Meta:
		database = db

class User(Model):
	uid = CharField(primary_key=True)
	username = CharField()
	class Meta:
		database = db

class Point(Model):
	sender = ForeignKeyField(User, related_name="sent_points")
	reciever = ForeignKeyField(User, related_name="recieved_points")
	channel = ForeignKeyField(Channel, related_name="points")
	ts = CharField()
	date = DateTimeField(default=datetime.datetime.now)
	class Meta:
		database = db

db.connect()

if config.SETTING_UP == True:
	db.create_tables([Channel, User, Point])

admins = config.ADMINS

if sc.rtm_connect():
	while True:
		event = sc.rtm_read()
		if len(event) > 0:
			event = event[0]
			if event["type"] == "message" and "text" in event:
				if config.LEADERBOARD_COMMAND in event["text"] and "<@" in event["text"]:
					userId = re.search('<(.*)>', event["text"]).group(1).replace("@", "")
					timestamp = event["ts"]
					fromUser = event["user"]
					try:
						date = datetime.date.today()
						lastSunday = date - datetime.timedelta(((date.weekday() + 1) % 7))
						recievedPoints = User.select().join(Point, on=Point.reciever).where(Point.date > lastSunday, User.uid == userId).count()
						sentPoints = User.select().join(Point, on=Point.sender).where(Point.date > lastSunday, User.uid == userId).count()
						
						message = "<@"+userId+"> has recieved *" + str(recievedPoints) + "* " + config.POINT_TEXT + "s and sent *" + str(sentPoints) + "* " + config.POINT_TEXT + "s this week."
						sc.api_call(
							"chat.postEphemeral",
							as_user=True,
							channel=str(event["channel"]),
							text=message,
							user=str(fromUser)
						)
					except User.DoesNotExist:
						sc.api_call(
							"chat.postEphemeral",
							channel=str(event["channel"]),
							text="<@"+userId+"> has not sent or recieved any " + config.POINT_TEXT + "s!",
							as_user=True,
							user=str(fromUser)
						)
					
				if config.LEADERBOARD_COMMAND in event["text"] and "<@" not in event["text"]:
					timestamp = event["ts"]
					rawUsers = User.select()
					allUsers = []
					for user in rawUsers:
						date = datetime.date.today()
						lastSunday = date - datetime.timedelta(((date.weekday() + 1) % 7))
						points = User.select().join(Point, on=Point.reciever).where(Point.date > lastSunday, User.uid == user.uid).count()
						totalPoints = len(user.recieved_points)
						if points > 0:
							allUsers.append({"id": user.uid, "username": user.username, "points": points, "totalPoints": totalPoints})
					
					allUsers = sorted(allUsers, key=itemgetter('points'), reverse=True)
					allUsers = allUsers[:5]
					
					userString = "*Leaderboard:*\n>>>"
					for index, user in enumerate(allUsers):
						userString += "\n" + str(index + 1) + ")  " + user["username"] + " *" + str(user["points"]) + "*-*" + str(user["totalPoints"]) + "*\n"
					
					sc.api_call(
						"chat.postMessage",
						channel=str(event["channel"]),
						text=userString,
						thread_ts=str(timestamp),
						as_user=True
					)
				if "<@" in event["text"] and (config.EMOJI in event["text"]):
					toUser = re.search('<(.*)>', event["text"]).group(1).replace("@", "")
					fromUser = event["user"]
					points = event["text"].count(config.EMOJI)
					if str(fromUser) in admins:
						if "(x" in event["text"]:
							points = int(re.search('\((.*)\)', event["text"]).group(1).replace("x", ""))
					channelId = event["channel"]
					timestamp = event["ts"]
					
					if toUser != fromUser or fromUser in admins:
						todayPoints = (User.select(fn.date_trunc('day', Point.date).alias('day'),fn.count(Point.id).alias('count')).join(Point, on=Point.sender).where(User.uid == str(fromUser)).group_by(fn.date_trunc('day', Point.date)))
						if len(todayPoints) > 0:
							todayPoints = todayPoints[0].count
						else:
							todayPoints = 0
						
						if todayPoints + points < (config.DAILY_LIMIT + 1) or str(fromUser) in admins or config.INFINITE_POINTS:
							todayPoints = todayPoints + points
							try:
								foundPoint = Point.get(Point.ts == timestamp)
							except Point.DoesNotExist:
								reciever = None
								try:
									reciever = User.get(User.uid == toUser)
								except User.DoesNotExist:
									userInfo = sc.api_call("users.info", user=toUser)["user"]
									reciever = User.create(uid=toUser, username=userInfo["name"])

								sender = None
								try:
									sender = User.get(User.uid == fromUser)
								except User.DoesNotExist:
									userInfo = sc.api_call("users.info", user=fromUser)["user"]
									sender = User.create(uid=fromUser, username=userInfo["name"])

								channel = None
								try:
									channel = Channel.get(Channel.uid == channelId)
								except Channel.DoesNotExist:
									channel = Channel.create(uid=channelId)

								for index in range(points):
									Point.create(sender=sender, reciever=reciever, channel=channel, ts=timestamp)
								
								date = datetime.date.today()
								lastSunday = date - datetime.timedelta(((date.weekday() + 1) % 7))
								weekPoints = User.select().join(Point, on=Point.reciever).where(Point.date > lastSunday, User.uid == reciever.uid).count()
								totalPoints = len(reciever.recieved_points)
								
								if config.INFINITE_POINTS:
									fromUserText = "You gave *" + str(points) + "* " + config.POINT_TEXT + "" + ("s" if points > 1 else "") + " to <@" + str(toUser) + ">!"
								else:
									fromUserText = "You gave *" + str(points) + "* " + config.POINT_TEXT + "" + ("s" if points > 1 else "") + " to <@" + str(toUser) + ">! You have *" + str(config.DAILY_LIMIT - todayPoints) + "* " + config.POINT_TEXT + "" + ("s" if (config.DAILY_LIMIT - todayPoints) > 1 else "") + " left today."
								
								sc.api_call(
									"chat.postEphemeral",
									channel=str(channelId),
									text=fromUserText,
									as_user=True,
									user=str(fromUser)
								)
								
								sc.api_call(
									"chat.postEphemeral",
									channel=str(channelId),
									text="<@" + str(fromUser) + "> gave you *" + str(points) + "* " + config.POINT_TEXT + "" + ("s" if points > 1 else "") + "! You have *" + str(weekPoints) + "* " + config.POINT_TEXT + "" + ("s" if weekPoints > 1 else "") + " this week, and *" + str(totalPoints) + "* " + config.POINT_TEXT + "" + ("s" if totalPoints > 1 else "") + " in total.",
									as_user=True,
									user=str(toUser)
								)
						else:
							if todayPoints == config.DAILY_LIMIT:
								sc.api_call(
									"chat.postEphemeral",
									channel=str(channelId),
									text="Sorry, but you can only give *" + str(config.DAILY_LIMIT) + "* " + config.EMOJI + " per day.",
									as_user=True,
									user=str(fromUser)
								)
							else:
								sc.api_call(
									"chat.postEphemeral",
									channel=str(channelId),
									text="Sorry, but you can only give " + (config.DAILY_LIMIT) + " " + config.EMOJI + " per day. You have *" + str(config.DAILY_LIMIT - todayPoints) + "* " + config.EMOJI + " left today.",
									as_user=True,
									user=str(fromUser)
								)
		time.sleep(1)

else:
	print "Connection Failed, invalid token?"