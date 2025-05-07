from flask_sqlalchemy import SQLAlchemy
from flask_security.core import Security
from flask_migrate import Migrate
from flask_mail import Mail
from authlib.integrations.flask_client import OAuth
from sqlalchemy.pool import QueuePool

db = SQLAlchemy(engine_options={
    "pool_pre_ping": True,  # Enable connection pre-ping to detect stale connections
    "pool_recycle": 300,    # Recycle connections after 5 minutes
    "pool_timeout": 30,     # Connection timeout after 30 seconds
    "poolclass": QueuePool  # Use QueuePool for connection pooling
})
security : Security = Security()
migrate : Migrate = Migrate()
mail : Mail = Mail()
oauth : OAuth = OAuth()
