import dotenv

from ttcli.config.config import source_config

source_config()

dotenv.load_dotenv(override=True)
