import os
from config import Config
from dotenv import load_dotenv

for env_file in ('.env', '.flaskenv'):
	env = os.path.join(os.getcwd(), env_file)
	if os.path.exists(env):
		load_dotenv(env)

from feedbook import create_app

app = create_app(Config)
