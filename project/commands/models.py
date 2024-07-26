from project import db


class AirConCommand(db.Model):

    __tablename__ = "aircon_command"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uid = db.Column(db.String(128), unique=True, nullable=False)
    temperature = db.Column(db.Integer, nullable=False)

    def __init__(self, uid, temperature, *args, **kwargs):
        self.uid = uid
        self.temperature = temperature