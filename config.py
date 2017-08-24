# Set to True the first time you run so that the database gets setup
SETTING_UP = True


# Slack Bot API Token
API_TOKEN = "YOUR_TOKEN_HERE"

# List of User ID's with admin privileges
ADMINS = [
	"USER_ID",
	"USER_ID",
	"USER_ID"
]

# Make sure that you include : on each side
EMOJI = ":+1:"

# Must be > 0, will be overridden by INFINITE_POINTS
DAILY_LIMIT = 6

# If set to True, DAILY_LIMIT is disregarded and every user gets infinite points
INFINITE_POINTS = True

# Command used to open the leaderboard
LEADERBOARD_COMMAND = "leaderboard"

# Singular form of point text. Eg: point, smile, emoji
POINT_TEXT = "point"