from flask import Flask
from ardana_server import playbooks, admin
import logging

LOG = logging.getLogger(__name__)
app = Flask(__name__)
app.register_blueprint(admin.bp)
app.register_blueprint(playbooks.bp)


if __name__ == "__main__":
    app.run(debug=True)
